
import typing
import datetime
import re

import tucal.db
import tucal.db as db
import tucal.icalendar as ical

COURSE_NR = re.compile(r'^([0-9]{3})\.([0-9A-Z]{3})')

CATEGORY_TYPES = {
    'OTHER': 0,
    'event_other': 0,
    'COURSE': 1,
    'event_course': 1,
    'GROUP': 2,
    'event_group': 2,
    'EXAM': 3,
    'event_exam': 3,
    'ORG': 4,
    'event_org': 4,
    'LEARN_SLOT': 5,
    'event_learn_slot': 5,
}


def get_course(name: str) -> typing.Optional[str]:
    course = COURSE_NR.findall(name)
    course = course[0][0] + course[0][1] if len(course) > 0 else None
    cur = tucal.db.cursor()
    cur.execute("SELECT course_nr FROM tiss.course_def WHERE course_nr = %s", (course,))
    courses = cur.fetchall()
    cur.close()
    if len(courses) == 0:
        return None
    else:
        return course


def insert_event_ical(evt: ical.Event, room_code: str = None, mnr: int = None) -> typing.Optional[int]:
    if evt.categories[0] == 'HOLIDAY':
        return

    cur = db.cursor()

    location = None
    if room_code is None and evt.location is not None:
        cur.execute("SELECT code FROM tiss.room WHERE name_full = %s", (evt.location,))
        codes = cur.fetchall()
        if len(codes) > 0:
            room_code = codes[0][0] if len(codes) > 0 else None
        else:
            location = evt.location
            room_code = None

    data = {
        'mnr': mnr,
        'id': int(evt.uid.split('@')[0].split('-')[1]),
        'type': CATEGORY_TYPES[evt.categories[0]],
        'name': evt.summary,
        'desc': evt.description,
        'room': room_code,
        'loc': location,
        'start': evt.start,
        'end': evt.end,
        'access': evt.access,
    }
    data['course'] = get_course(data['name'])

    cur.execute("""
        SELECT event_nr FROM tiss.event
        WHERE event_id = %(id)s
        UNION ALL
        SELECT event_nr FROM tiss.event
        WHERE event_id IS NULL AND
        (room_code IS NULL OR %(room)s IS NULL OR COALESCE(room_code, '') = COALESCE(%(room)s, '')) AND
        (type, name, start_ts, end_ts) = (%(type)s, %(name)s, %(start)s, %(end)s)""", data)
    events = cur.fetchall()

    if len(events) > 0:
        data['nr'] = events[0][0]
        cur.execute("""
            UPDATE tiss.event SET event_id = %(id)s, type = %(type)s, start_ts = %(start)s, end_ts = %(end)s,
                access_ts = %(access)s, name = %(name)s, description = %(desc)s, course_nr = %(course)s,
                location = %(loc)s
            WHERE event_nr = %(nr)s""", data)
        if room_code is not None:
            cur.execute("UPDATE tiss.event SET room_code = %(room)s WHERE event_nr = %(nr)s", data)
    else:
        cur.execute("""
            INSERT INTO tiss.event (event_id, type, room_code, start_ts, end_ts, access_ts, name, description,
                course_nr, location)
            VALUES (%(id)s, %(type)s, %(room)s, %(start)s, %(end)s, %(access)s, %(name)s, %(desc)s, %(course)s, %(loc)s)
            RETURNING event_nr""", data)
        events = cur.fetchall()
        data['nr'] = events[0][0]

    if mnr is not None:
        cur.execute("""
            INSERT INTO tiss.event_user (event_nr, mnr)
            VALUES (%(nr)s, %(mnr)s) ON CONFLICT DO NOTHING""", data)

    cur.close()
    return data['nr']


def insert_event(evt: typing.Dict[str, typing.Any], access_time: datetime.datetime, room_code: str = None,
                 mnr: int = None) -> typing.Optional[int]:
    classes = evt['className'].split(' ')
    if classes[0] == 'holiday':
        return None

    cur = db.cursor()

    data = {
        'mnr': mnr,
        'type': CATEGORY_TYPES[classes[0]],
        'live': 'livestream' in classes,
        'online': 'no_attendance' in classes,
        'start': tucal.parse_iso_timestamp(evt['start'], True),
        'end': tucal.parse_iso_timestamp(evt['end'], True),
        'access': access_time,
        'name': evt['title'],
        'room': room_code,
    }
    data['course'] = get_course(data['name'])

    cur.execute("""
        SELECT event_nr FROM tiss.event
        WHERE (room_code IS NULL OR %(room)s IS NULL OR COALESCE(room_code, '') = COALESCE(%(room)s, '')) AND
        (type, name, start_ts, end_ts) = (%(type)s, %(name)s, %(start)s, %(end)s)""", data)
    events = cur.fetchall()

    if len(events) > 0:
        data['nr'] = events[0][0]
        cur.execute("""
            UPDATE tiss.event
            SET type = %(type)s, start_ts = %(start)s, end_ts = %(end)s, access_ts = %(access)s, name = %(name)s,
                livestream = %(live)s, online_only = %(online)s, course_nr = %(course)s
            WHERE event_nr = %(nr)s""", data)
        if room_code is not None:
            cur.execute("UPDATE tiss.event SET room_code = %(room)s WHERE event_nr = %(nr)s", data)
    else:
        cur.execute("""
            INSERT INTO tiss.event (type, room_code, start_ts, end_ts, access_ts, name, description,
                livestream, online_only, course_nr) 
            VALUES (%(type)s, %(room)s, %(start)s, %(end)s, %(access)s, %(name)s, NULL, %(live)s, %(online)s,
                %(course)s)
            RETURNING event_nr""", data)
        events = cur.fetchall()
        data['nr'] = events[0][0]

    if mnr is not None:
        cur.execute("""
            INSERT INTO tiss.event_user (event_nr, mnr) 
            VALUES (%(nr)s, %(mnr)s) ON CONFLICT DO NOTHING""", data)

    cur.close()
    return data['nr']
