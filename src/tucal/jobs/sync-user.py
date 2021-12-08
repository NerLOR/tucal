#!/bin/env python3

import datetime
import argparse

from tucal import Job
import tuwien.tuwel
import tuwien.tiss
import tuwien.sso
import tucal.db
import tucal.db.tiss
import tucal.db.tuwel


TUWEL_INIT_VAL = 1
TUWEL_MONTHS = 12
TUWEL_MONTH_VAL = 1
TISS_VAL = 10


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mnr', '-m', required=True,
                        help='Matriculation number')
    parser.add_argument('--keep-calendar-settings', '-k', action='store_true', default=False,
                        help='Do not alter any TISS calendar settings')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--store', '-s', action='store_true', default=False,
                       help='Store provided password (and 2fa generator) in database')
    group.add_argument('--database', '-d', action='store_true', default=False,
                       help='Fetch password (and 2fa token) from database')
    args = parser.parse_args()

    mnr = args.mnr
    pwd = None
    tfa_token = None
    tfa_gen = None
    if not args.database:
        pwd = input()
        tfa = input()
        tfa = None if len(tfa) == 0 else tfa
    else:
        pass  # TODO

    cur = tucal.db.cursor()

    now = datetime.datetime.now().astimezone()
    job = Job('sync user', 2, TUWEL_MONTHS * TUWEL_MONTH_VAL + TUWEL_INIT_VAL + TISS_VAL)

    sso = tuwien.sso.Session()
    sso.credentials(mnr, pwd)

    job.begin('sync tiss')
    tiss = tuwien.tiss.Session(sso)
    tiss.sso_login()

    tiss_cal_token = tiss.calendar_token

    cur.execute(
        "INSERT INTO tiss.user (mnr, auth_token, last_sync) VALUES (%s, %s, %s) "
        "ON CONFLICT ON CONSTRAINT pk_user DO UPDATE SET auth_token = %s, last_sync = %s",
        (mnr, tiss_cal_token, now, tiss_cal_token, now)
    )

    cur.execute("DELETE FROM tiss.course_user WHERE mnr = %s", (mnr,))
    cur.execute("DELETE FROM tiss.group_user WHERE mnr = %s", (mnr,))
    cur.execute("DELETE FROM tiss.exam_user WHERE mnr = %s", (mnr,))
    for course in tiss.favorites:
        cur.execute("INSERT INTO tiss.course_user (course_nr, semester, mnr) VALUES (%s, %s, %s)",
                    (course.nr, str(course.semester), mnr))
        tiss.get_groups(course)

    if not args.keep_calendar_settings:
        tiss.update_calendar_settings()

    data = tiss.get_personal_schedule()
    for evt in data['events']:
        tucal.db.tiss.insert_event(evt, now, mnr=mnr)

    job.end(TISS_VAL)

    job.begin('sync tuwel', 2)
    job.begin('init tuwel')
    tuwel = tuwien.tuwel.Session(sso)
    tuwel.sso_login()

    tuwel_cal_token = tuwel.calendar_token
    user_id = tuwel.user_id
    courses = tuwel.courses

    cur.execute(
        "INSERT INTO tuwel.user (user_id, mnr, auth_token, last_sync) VALUES (%s, %s, %s, %s)"
        "ON CONFLICT ON CONSTRAINT pk_user DO UPDATE SET mnr = %s, auth_token = %s, last_sync = %s",
        (user_id, mnr, tuwel_cal_token, now, mnr, tuwel_cal_token, now)
    )
    cur.execute("DELETE FROM tuwel.course_user WHERE user_id = %s", (user_id,))

    for c in courses.values():
        cur.execute(
            "INSERT INTO tuwel.course (course_id, course_nr, semester, name, suffix, short) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT ON CONSTRAINT pk_course "
            "DO UPDATE SET course_nr = %s, semester = %s, name = %s, suffix = %s, short = %s",
            (c.id, c.nr, str(c.semester), c.name, c.suffix, c.short, c.nr, str(c.semester), c.name, c.suffix, c.short)
        )
        cur.execute("INSERT INTO tuwel.course_user (course_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (c.id, user_id))
    job.end(TUWEL_INIT_VAL)

    job.begin('sync tuwel calendar months', TUWEL_MONTHS)
    acc = datetime.datetime.utcnow()
    months = [(acc.year + (acc.month - i - 1) // 12, (acc.month - i + 11) % 12 + 1) for i in range(0, TUWEL_MONTHS)]

    events = []
    for year, month in months[::-1]:
        job.begin(f'sync tuwel calendar month {month}/{year}')
        r = tuwel.ajax('core_calendar_get_calendar_monthly_view', year=year, month=month)
        events += [
            evt
            for week in r['data']['weeks']
            for day in week['days']
            for evt in day['events']
        ]
        job.end(TUWEL_MONTH_VAL)
    job.end(0)

    for evt in events:
        tucal.db.tuwel.insert_event(evt, acc, user_id)
    job.end(0)

    cur.close()
    tucal.db.commit()

    job.end(0)
