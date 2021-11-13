#!/bin/env python3

import sys
import requests
import datetime

import tucal.db
import tucal.icalendar
import tuwien.tuwel

if __name__ == '__main__':
    cur = tucal.db.cursor()
    cur.execute("SELECT user_id, auth_token FROM tuwel.user")
    for user_id, token in cur.fetchall():
        url = f'{tuwien.tuwel.TUWEL_URL}/calendar/export_execute.php?userid={user_id}&authtoken={token}&preset_what=all'
        r = requests.get(f'{url}&preset_time=custom')  # 1 year from today and last 7 (?) days

        if r.status_code != 200:
            print(f'Invalid token for user {user_id}, deleting token', file=sys.stderr)
            cur.execute("UPDATE tuwel.user SET auth_token = NULL WHERE user_id = %s", (user_id,))
            continue

        cal = tucal.icalendar.parse_ical(r.text)

        cur.execute("DELETE FROM tuwel.event_user eu WHERE user_id = %s AND "
                    "(SELECT start_ts FROM tuwel.event e WHERE e.event_id = eu.event_id) >= %s",
                    (user_id, datetime.date.today() - datetime.timedelta(days=5)))

        for evt in cal.events:
            evt_id = evt.uid.split('@')[0]
            cur.execute("INSERT INTO tuwel.event (event_id, course_id, start_ts, end_ts, access_ts, mod_ts, name,"
                        "description) "
                        "VALUES (%s, (SELECT course_id FROM tuwel.course WHERE short = %s), %s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT ON CONSTRAINT pk_event "
                        "DO UPDATE SET start_ts = %s, end_ts = %s, access_ts = %s, mod_ts = %s, name = %s, "
                        "description = %s",
                        (evt_id, evt.categories[0], evt.start, evt.end, evt.access, evt.last_modified, evt.summary,
                         evt.description, evt.start, evt.end, evt.access, evt.last_modified, evt.summary,
                         evt.description))
            cur.execute("INSERT INTO tuwel.event_user (event_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (evt_id, user_id))
    cur.close()
    tucal.db.commit()
