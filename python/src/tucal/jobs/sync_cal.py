
import re
import argparse
import sys

from tucal import Semester, Job
import tucal.db
import tucal.db.tiss
import tucal.db.tuwel
import tucal.icalendar
import tuwien.tiss
import tuwien.tuwel

COURSE = re.compile(r'^([0-9]{3}\.[0-9A-Z]{3})')


def sync_cal(mnr: int = None, job: Job = None):
    job = job or Job()

    cur = tucal.db.cursor()
    tiss = tuwien.tiss.Session()
    tuwel = tuwien.tuwel.Session()

    cur.execute("SELECT code, name FROM tiss.room")
    rooms = cur.fetch_all()
    cur.execute("SELECT mnr, auth_token FROM tiss.user WHERE auth_token IS NOT NULL")
    tiss_users = cur.fetch_all()
    tiss_mnr = [u[0] for u in tiss_users]
    cur.execute("SELECT user_id, mnr, auth_token FROM tuwel.user WHERE auth_token IS NOT NULL")
    tuwel_users = cur.fetch_all()
    tuwel_mnr = [u[1] for u in tuwel_users]

    if mnr is not None:
        tiss_num = 1 if mnr in tiss_mnr else 0
        tuwel_num = 1 if mnr in tuwel_mnr else 0
        job.init('sync user calendars', 2, tiss_num + tuwel_num)
    else:
        tiss_num = len(tiss_users)
        tuwel_num = len(tuwel_users)
        job.init('sync calendars', 3, len(rooms) + len(tiss_users) + len(tuwel_users))

    # FIXME db.commit or db.rollback to stop blocking other connections
    if mnr is None:
        job.begin('sync tiss room schedules', len(rooms))
        for room_code, room_name in rooms:
            job.begin(f'sync tiss room schedule {room_name} <{room_code}>')
            access = tucal.now()

            cal = tiss.get_room_schedule_ical(room_code)
            for evt in cal.events:
                tucal.db.tiss.upsert_ical_event(evt, room_code)
            tucal.db.commit()

            cal = tiss.get_room_schedule(room_code)
            for evt in cal['events']:
                tucal.db.tiss.upsert_event(evt, access, room_code)
            tucal.db.commit()
            job.end(1)
        job.end(0)

    job.begin('sync tiss personal calendars', tiss_num)
    for t_mnr, token in tiss_users:
        if mnr is not None and mnr != t_mnr:
            continue
        job.begin(f'sync tiss personal calendar {t_mnr}')

        cal = tiss.get_personal_schedule_ical(token)
        if cal is None:
            print(f'Invalid token for user {t_mnr}, deleting token', file=sys.stderr)
            cur.execute("UPDATE tiss.user SET auth_token = NULL WHERE mnr = %s", (t_mnr,))
            job.end(1)
            continue

        cur.execute("""
            DELETE FROM tiss.event_user eu
            WHERE mnr = %s AND
                  (SELECT start_ts
                   FROM tiss.event e
                   WHERE e.event_nr = eu.event_nr) >= %s""", (t_mnr, Semester.current().first_day))

        for evt in cal.events:
            tucal.db.tiss.upsert_ical_event(evt, mnr=t_mnr)
        tucal.db.commit()
        job.end(1)
    job.end(0)

    job.begin('sync tuwel personal calendars', tuwel_num)
    for user_id, t_mnr, token in tuwel_users:
        if mnr is not None and mnr != t_mnr:
            continue
        job.begin(f'sync tuwel personal calendar {t_mnr}')

        cal = tuwel.get_personal_calendar(token, user_id=user_id)
        if cal is None:
            print(f'Invalid token for user {user_id}, deleting token', file=sys.stderr)
            cur.execute("UPDATE tuwel.user SET auth_token = NULL WHERE user_id = %s", (user_id,))
            job.end(1)
            continue

        cur.execute("""
            DELETE FROM tuwel.event_user eu
            WHERE user_id = %s AND
                  (SELECT start_ts >= now()
                   FROM tuwel.event e
                   WHERE e.event_id = eu.event_id)""", (user_id,))

        for evt in cal.events:
            tucal.db.tuwel.upsert_ical_event(evt, user_id)
        tucal.db.commit()
        job.end(1)
    job.end(0)

    cur.close()
    job.end(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mnr', '-m', type=int)
    args = parser.parse_args()
    sync_cal(args.mnr)
