
import re
import argparse
import datetime
import sys

from tucal import Semester, Job
import tucal.db
import tucal.db.tiss
import tucal.db.tuwel
import tucal.icalendar
import tuwien.tiss
import tuwien.tuwel

COURSE = re.compile(r'^([0-9]{3}\.[0-9A-Z]{3})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mnr', '-m', type=int)
    args = parser.parse_args()

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

    if args.mnr is not None:
        tiss_num = 1 if args.mnr in tiss_mnr else 0
        tuwel_num = 1 if args.mnr in tuwel_mnr else 0
        job = Job('sync user calendars', 2, tiss_num + tuwel_num)
    else:
        tiss_num = len(tiss_users)
        tuwel_num = len(tuwel_users)
        job = Job('sync calendars', 3, len(rooms) + len(tiss_users) + len(tuwel_users))

    # FIXME db.commit or db.rollback to stop blocking other connections
    if args.mnr is None:
        job.begin('sync tiss room schedules', len(rooms))
        for room_code, room_name in rooms:
            job.begin(f'sync tiss room schedule {room_name} <{room_code}>')
            access = tucal.now()

            cal = tiss.get_room_schedule_ical(room_code)
            for evt in cal.events:
                tucal.db.tiss.insert_event_ical(evt, room_code)
            tucal.db.commit()

            cal = tiss.get_room_schedule(room_code)
            for evt in cal['events']:
                tucal.db.tiss.insert_event(evt, access, room_code)
            tucal.db.commit()
            job.end(1)
        job.end(0)

    job.begin('sync tiss personal calendars', tiss_num)
    for mnr, token in tiss_users:
        if args.mnr is not None and mnr != args.mnr:
            continue
        job.begin(f'sync tiss personal calendar {mnr}')

        cal = tiss.get_personal_schedule_ical(token)
        if cal is None:
            print(f'Invalid token for user {mnr}, deleting token', file=sys.stderr)
            cur.execute("UPDATE tiss.user SET auth_token = NULL WHERE mnr = %s", (mnr,))
            job.end(1)
            continue

        cur.execute("""
            DELETE FROM tiss.event_user eu
            WHERE mnr = %s AND
                  (SELECT start_ts
                   FROM tiss.event e
                   WHERE e.event_nr = eu.event_nr) >= %s""", (mnr, Semester.current().first_day))

        for evt in cal.events:
            tucal.db.tiss.insert_event_ical(evt, mnr=mnr)
        tucal.db.commit()
        job.end(1)
    job.end(0)

    job.begin('sync tuwel personal calendars', tuwel_num)
    time = datetime.date.today() - datetime.timedelta(days=5)
    for user_id, mnr, token in tuwel_users:
        if args.mnr is not None and mnr != args.mnr:
            continue
        job.begin(f'sync tuwel personal calendar {mnr}')

        cal = tuwel.get_personal_calendar(token, user_id=user_id)
        if cal is None:
            print(f'Invalid token for user {user_id}, deleting token', file=sys.stderr)
            cur.execute("UPDATE tuwel.user SET auth_token = NULL WHERE user_id = %s", (user_id,))
            job.end(1)
            continue

        # TUWEL omits "Ankreuzen" events if no user is logged in to the current session
        cur.execute("""
            DELETE FROM tuwel.event_user eu
            WHERE user_id = %s AND
                  (SELECT start_ts >= %s AND
                          NOT name ILIKE '%%Ankreuzen%%' AND
                          NOT name ILIKE '%%Anmeldedeadline%%'
                   FROM tuwel.event e
                   WHERE e.event_id = eu.event_id)""", (user_id, time))

        for evt in cal.events:
            tucal.db.tuwel.insert_event_ical(evt, user_id)
        tucal.db.commit()
        job.end(1)
    job.end(0)

    cur.close()
    job.end(0)
