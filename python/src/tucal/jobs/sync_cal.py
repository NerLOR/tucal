
from typing import Optional, List, Tuple, Dict, Any, Set
import re
import argparse
import sys
import datetime

from tucal import Semester, Job
import tucal.db
import tucal.db.tiss
import tucal.db.tuwel
import tucal.icalendar
import tuwien.tiss
import tuwien.tuwel
import tuwien.sso

COURSE = re.compile(r'^([0-9]{3}\.[0-9A-Z]{3})')


class SyncCalendar(tucal.Sync):
    job: Job
    mnr: Optional[str]
    mnr_int: Optional[int]

    access_time: datetime.datetime = None
    rooms: List[Tuple[str, str]] = None
    tiss_users: List[Tuple[int, str]] = None
    tuwel_users: List[Tuple[int, int, str]] = None
    tiss_mnr: Set[int] = None
    tuwel_mnr: Set[int] = None

    tiss_room_calendars: Dict[str, tucal.icalendar.Calendar] = None
    tiss_room_schedules: Dict[str, Dict[str, Any]] = None
    tiss_user_calendars: Dict[int, tucal.icalendar.Calendar] = None
    tuwel_calendars: Dict[int, tucal.icalendar.Calendar] = None

    def __init__(self, session: tuwien.sso.Session, mnr: int = None, job: Job = None):
        super().__init__(session)
        self.job = job or Job()
        self.mnr = f'{mnr:08}' if mnr else None
        self.mnr_int = int(mnr) if mnr else None

    def init_info(self):
        if self.rooms and self.tiss_users and self.tiss_mnr and self.tuwel_users and self.tuwel_mnr:
            return

        cur = tucal.db.cursor()
        cur.execute("SELECT code, name FROM tiss.room")
        self.rooms = cur.fetch_all()

        cur.execute("SELECT mnr, auth_token FROM tiss.user WHERE auth_token IS NOT NULL")
        self.tiss_users = cur.fetch_all()
        self.tiss_mnr = {u[0] for u in self.tiss_users}

        cur.execute("SELECT user_id, mnr, auth_token FROM tuwel.user WHERE auth_token IS NOT NULL")
        self.tuwel_users = cur.fetch_all()
        self.tuwel_mnr = {u[1] for u in self.tuwel_users}

        cur.close()
        tucal.db.rollback()

    def fetch(self):
        tiss = tuwien.tiss.Session()
        tuwel = tuwien.tuwel.Session()
        self.access_time = tucal.now()

        self.init_info()

        if self.mnr_int:
            tiss_num = 1 if self.mnr_int in self.tiss_mnr else 0
            tuwel_num = 1 if self.mnr_int in self.tuwel_mnr else 0
            val = tiss_num + tuwel_num
        else:
            tiss_num = len(self.tiss_users)
            tuwel_num = len(self.tuwel_users)
            val = tiss_num + tuwel_num + len(self.rooms) * 2

        self.job.init('fetch calendars', 3 if not self.mnr_int else 2, val)

        if not self.mnr_int:
            self.job.begin('sync tiss room schedules', len(self.rooms))
            self.tiss_room_calendars = {}
            for room_code, room_name in self.rooms:
                self.job.begin(f'sync tiss room schedule {room_name} <{room_code}>')
                self.tiss_room_calendars[room_code] = tiss.get_room_schedule_ical(room_code)
                self.tiss_room_schedules[room_code] = tiss.get_room_schedule(room_code)
                self.job.end(2)
            self.job.end(0)

        self.job.begin('sync tiss personal calendars', tiss_num)
        self.tiss_user_calendars = {}
        for mnr, token in self.tiss_users:
            if self.mnr_int and self.mnr_int != mnr:
                continue
            self.job.begin(f'sync tiss personal calendar {mnr}')
            self.tiss_user_calendars[mnr] = tiss.get_personal_schedule_ical(token)
            if self.tiss_user_calendars[mnr] is None:
                print(f'Invalid token for user {mnr}, deleting token', file=sys.stderr)
            self.job.end(1)
        self.job.end(0)

        self.job.begin('sync tuwel personal calendars', tuwel_num)
        self.tuwel_calendars = {}
        for user_id, t_mnr, token in self.tuwel_users:
            if self.mnr_int and self.mnr_int != t_mnr:
                continue
            self.job.begin(f'sync tuwel personal calendar {t_mnr}')
            self.tuwel_calendars[user_id] = tuwel.get_personal_calendar(token, user_id=user_id)
            if self.tuwel_calendars[user_id] is None:
                print(f'Invalid token for user {user_id}, deleting token', file=sys.stderr)
            self.job.end(1)
        self.job.end(0)

        self.job.end(0)

    def store(self, cur: tucal.db.Cursor):
        self.job.init('store calendars', 0, 1)

        if not self.mnr_int:
            for room_code, cal in self.tiss_room_calendars.items():
                for evt in cal.events:
                    tucal.db.tiss.upsert_ical_event(evt, room_code)

            for room_code, cal in self.tiss_room_schedules.items():
                for evt in cal['events']:
                    tucal.db.tiss.upsert_event(evt, self.access_time, room_code)

        for mnr, cal in self.tiss_user_calendars.items():
            if cal is None:
                cur.execute("UPDATE tiss.user SET auth_token = NULL WHERE mnr = %s", (mnr,))
                continue

            cur.execute("""
                DELETE FROM tiss.event_user eu
                WHERE mnr = %s AND
                      (SELECT start_ts
                       FROM tiss.event e
                       WHERE e.event_nr = eu.event_nr) >= %s""", (mnr, Semester.current().first_day))

            for evt in cal.events:
                tucal.db.tiss.upsert_ical_event(evt, mnr=mnr)

        for user_id, cal in self.tuwel_calendars.items():
            if cal is None:
                cur.execute("UPDATE tuwel.user SET auth_token = NULL WHERE user_id = %s", (user_id,))
                continue

            cur.execute("""
                DELETE FROM tuwel.event_user eu
                WHERE user_id = %s AND
                      (SELECT start_ts >= now()
                       FROM tuwel.event e
                       WHERE e.event_id = eu.event_id)""", (user_id,))

            tucal.db.tuwel.upsert_ical_events(cal.events, user_id)

        self.job.end(1)

    def sync(self, cur: tucal.db.Cursor):
        self.init_info()
        v = 1
        if self.mnr_int:
            tiss_num = 1 if self.mnr_int in self.tiss_mnr else 0
            tuwel_num = 1 if self.mnr_int in self.tuwel_mnr else 0
            v += tiss_num + tuwel_num
            self.job.init('sync user calendars', 2, v)
        else:
            v += len(self.rooms) + len(self.tiss_users) + len(self.tuwel_users)
            self.job.init('sync calendars', 3, v)

        self.job.exec(v - 1, self.fetch, False)
        self.job.exec(1, self.store, False, cur=cur)
        self.job.end(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mnr', '-m', type=int)
    args = parser.parse_args()

    sync_cal = SyncCalendar(tuwien.sso.Session(), args.mnr)
    sync_cal.sync(tucal.db.cursor())
    tucal.db.commit()
