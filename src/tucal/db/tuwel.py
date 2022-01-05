
from typing import Dict, Any
import datetime

import tucal.icalendar as ical
import tucal.db as db


def insert_event_ical(evt: ical.Event, user_id: int = None):
    cur = db.cursor()

    data = {
        'id': evt.uid.split('@')[0],
        'short': evt.categories[0],
        'start': evt.start,
        'end': evt.end,
        'access': evt.access,
        'mod': evt.last_modified,
        'name': evt.summary,
        'desc': evt.description,
        'user': user_id
    }

    cur.execute("""
        INSERT INTO tuwel.event (event_id, course_id, start_ts, end_ts, access_ts, mod_ts, name, description) 
        VALUES (%(id)s, (SELECT course_id FROM tuwel.course WHERE short = %(short)s), %(start)s, %(end)s, %(access)s,
        %(mod)s, %(name)s, %(desc)s) 
        ON CONFLICT ON CONSTRAINT pk_event DO UPDATE
        SET start_ts = %(start)s, end_ts = %(end)s, access_ts = %(access)s, mod_ts = %(mod)s, name = %(name)s,
            description = %(desc)s""", data)

    if user_id is not None:
        cur.execute("""
            INSERT INTO tuwel.event_user (event_id, user_id) 
            VALUES (%(id)s, %(user)s)
            ON CONFLICT DO NOTHING""", data)

    cur.close()


def insert_event(evt: Dict[str, Any], access_time: datetime.datetime, user_id: int = None):
    cur = db.cursor()

    start = datetime.datetime.fromtimestamp(evt['timestart']).astimezone()
    data = {
        'id': evt['id'],
        'name': evt['name'],
        'course': evt['course']['id'],
        'start': start,
        'end': start + datetime.timedelta(seconds=evt['timeduration']),
        'mod': datetime.datetime.fromtimestamp(evt['timemodified']).astimezone(),
        'access': access_time,
        'user': user_id
    }

    cur.execute("""
        INSERT INTO tuwel.event (event_id, course_id, start_ts, end_ts, access_ts, mod_ts, name, description)
        VALUES (%(id)s, %(course)s, %(start)s, %(end)s, %(access)s, %(mod)s, %(name)s, NULL)
        ON CONFLICT ON CONSTRAINT pk_event DO UPDATE
        SET start_ts = %(start)s, end_ts = %(end)s, access_ts = %(access)s, mod_ts = %(mod)s,
            name = %(name)s""", data)

    if user_id is not None:
        cur.execute("""
            INSERT INTO tuwel.event_user (event_id, user_id)
            VALUES (%(id)s, %(user)s)
            ON CONFLICT DO NOTHING""", data)

    cur.close()
    return

