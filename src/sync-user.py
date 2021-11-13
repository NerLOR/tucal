#!/bin/env python3

import datetime
import argparse

import tuwien.tuwel
import tuwien.sso
import tucal.db


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mnr')
    args = parser.parse_args()

    mnr = args.mnr
    pwd = input()

    sso = tuwien.sso.Session()
    sso.credentials(mnr, pwd)

    s = tuwien.tuwel.Session(sso)
    s.sso_login()

    calendar_token = s.calendar_token
    user_id = s.user_id
    courses = s.courses

    cur = tucal.db.cursor()

    cur.execute("INSERT INTO tuwel.user (user_id, mnr, auth_token) VALUES (%s, %s, %s)"
                "ON CONFLICT ON CONSTRAINT pk_user DO UPDATE SET mnr = %s, auth_token = %s",
                (user_id, mnr, calendar_token, mnr, calendar_token))

    for c in courses.values():
        cur.execute("INSERT INTO tuwel.course (course_id, course_nr, semester, name, suffix, short) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT ON CONSTRAINT pk_course "
                    "DO UPDATE SET course_nr = %s, semester = %s, name = %s, suffix = %s, short = %s",
                    (c.id, c.nr, str(c.semester), c.name, c.suffix, c.short, c.nr, str(c.semester), c.name, c.suffix,
                     c.short))

    acc = datetime.datetime.utcnow()
    months = [(acc.year + (acc.month - i - 1) // 12, (acc.month - i + 11) % 12 + 1) for i in range(0, 6)]

    events = []
    for year, month in months[::-1]:
        r = s.ajax('core_calendar_get_calendar_monthly_view', year=year, month=month)
        events += [
            evt
            for week in r['data']['weeks']
            for day in week['days']
            for evt in day['events']
        ]

    for evt in events:
        evt_id = evt['id']
        evt_name = evt['name']
        course_id = evt['course']['id']
        start = datetime.datetime.fromtimestamp(evt['timestart']).astimezone()
        end = start + datetime.timedelta(seconds=evt['timeduration'])
        mod = datetime.datetime.fromtimestamp(evt['timemodified']).astimezone()

        cur.execute("INSERT INTO tuwel.event (event_id, course_id, start_ts, end_ts, access_ts, mod_ts, name, "
                    "description) VALUES (%s, %s, %s, %s, %s, %s, %s, NULL) "
                    "ON CONFLICT ON CONSTRAINT pk_event "
                    "DO UPDATE SET start_ts = %s, end_ts = %s, access_ts = %s, mod_ts = %s, name = %s",
                    (evt_id, course_id, start, end, acc, mod, evt_name, start, end, acc, mod, evt_name))
        cur.execute("INSERT INTO tuwel.event_user (event_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING ",
                    (evt_id, user_id))

    cur.close()
    tucal.db.commit()
