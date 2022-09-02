
from typing import Optional, List, Dict, Any
import datetime
import re
import json

import tucal.db
import tucal.db as db
import tucal.icalendar as ical
from tuwien.tiss import Course

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


def get_course(name: str) -> Optional[str]:
    cur = tucal.db.cursor()
    course = COURSE_NR.findall(name)
    course = course[0][0] + course[0][1] if len(course) > 0 else None

    cur.execute("SELECT course_nr FROM tiss.course_def WHERE course_nr = %s", (course,))
    courses = cur.fetch_all()
    if len(courses) > 0:
        cur.close()
        return course

    cur.execute("SELECT course_nr FROM tiss.course_def WHERE name_de = %s", (name,))
    courses = cur.fetch_all()
    if len(courses) == 1:
        cur.close()
        return courses[0][0]

    cur.close()
    return None


def get_holiday_group_nr() -> int:
    cur = tucal.db.cursor()
    cur.execute("SELECT group_nr FROM tucal.group WHERE group_name = 'Holidays'")
    rows = cur.fetch_all()
    if len(rows) > 0:
        cur.close()
        return rows[0][0]

    cur.execute("INSERT INTO tucal.group (group_name, public) VALUES ('Holidays', TRUE) RETURNING group_nr")
    rows = cur.fetch_all()
    cur.close()
    return rows[0][0]


def upsert_holidays(events: List[Dict[str, Any]]):
    cur = db.cursor()
    group_nr = get_holiday_group_nr()

    for evt in events:
        norm = f'{evt["start"]}-{evt["name"].split(",")[0].replace(" ", "-").lower()}'
        data = {
            'id': norm,
            'start': tucal.date_to_datetime(evt['start'], True),
            'end': tucal.date_to_datetime(evt['end'], True),
            'group': group_nr,
            'data': json.dumps({
                'holidays': {
                    'name': evt['name'],
                },
            }),
        }
        cur.execute("""
            INSERT INTO tucal.external_event (source, event_id, start_ts, end_ts, group_nr, data)
            VALUES ('holidays', %(id)s, %(start)s, %(end)s, %(group)s, %(data)s)
            ON CONFLICT ON CONSTRAINT pk_external_event DO UPDATE
            SET start_ts = %(start)s, end_ts = %(end)s, group_nr = %(group)s, data = %(data)s""", data)

    cur.close()


def upsert_ical_events(events: List[ical.Event], room_code: str = None, mnr: int = None):
    cur = db.cursor()

    cur.execute("SELECT event_id, event_nr FROM tiss.event")
    evt_ids = {evt[0]: evt[1] for evt in cur.fetch_all()}

    courses = {}
    locations = {}
    rows_insert = []
    rows_update = []
    holidays = []
    for evt in events:
        if evt.categories[0] == 'HOLIDAY':
            holidays.append({
                'name': evt.summary,
                'start': evt.start,
                'end': evt.end,
            })
            continue

        location = None
        room = room_code
        if room_code is None and evt.location is not None:
            if evt.location in locations:
                room = locations[evt.location]
            else:
                cur.execute("SELECT code FROM tiss.room WHERE name_full = %s", (evt.location,))
                codes = cur.fetch_all()
                if len(codes) > 0:
                    room = codes[0][0] if len(codes) > 0 else None
                else:
                    location = evt.location
                    room = None
                locations[evt.location] = room

        data = {
            'mnr': mnr,
            'id': int(evt.uid.split('@')[0].split('-')[1]),
            'type': CATEGORY_TYPES[evt.categories[0]],
            'name': evt.summary,
            'desc': evt.description,
            'room': room,
            'loc': location,
            'start': evt.start,
            'end': evt.end,
            'access': evt.access,
        }
        data['course'] = data['name'] in courses and courses[data['name']] or get_course(data['name'])
        courses[data['name']] = data['course']

        if data['id'] in evt_ids:
            data['nr'] = evt_ids[data['id']]
            rows_update.append(data)
        else:
            cur.execute("""
                SELECT event_nr FROM tiss.event
                WHERE event_id IS NULL AND
                      (room_code IS NULL OR %(room)s IS NULL OR COALESCE(room_code, '') = COALESCE(%(room)s, '')) AND
                      (type, name, start_ts, end_ts) = (%(type)s, %(name)s, %(start)s, %(end)s)""", data)
            event_nrs = cur.fetch_all()

            if len(event_nrs) > 0:
                data['nr'] = event_nrs[0][0]
                rows_update.append(data)
            else:
                rows_insert.append(data)

    if len(rows_update) > 0:
        cur.execute_values("""
            UPDATE tiss.event SET event_id = d.id, type = d.type, start_ts = d.start_ts, end_ts = d.end_ts,
                access_ts = d.access, name = d.name, description = d.description, course_nr = d.course,
                location = d.loc
            FROM (VALUES (%(nr)s, %(id)s, %(type)s, %(start)s, %(end)s, %(access)s, %(name)s, %(desc)s, %(course)s,
                          %(loc)s)) AS
                 d (nr, id, type, start_ts, end_ts, access, name, description, course, loc)
            WHERE event_nr = d.nr""", rows_update)
        if room_code is not None:
            cur.execute_values("UPDATE tiss.event SET room_code = %(room)s WHERE event_nr = %(nr)s", rows_update)

    inserted = []
    if len(rows_insert) > 0:
        cur.execute_values("""
            INSERT INTO tiss.event (event_id, type, room_code, start_ts, end_ts, access_ts, name, description,
                course_nr, location)
            VALUES (%(id)s, %(type)s, %(room)s, %(start)s, %(end)s, %(access)s, %(name)s, %(desc)s, %(course)s, %(loc)s)
            RETURNING event_nr""", rows_insert)
        inserted = cur.fetch_all()
    evt_nrs = inserted + [evt['nr'] for evt in rows_update]

    if mnr and len(evt_nrs) > 0:
        cur.execute_values("""
            INSERT INTO tiss.event_user (event_nr, mnr)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING""", [(evt, mnr) for evt in evt_nrs])

    if len(holidays) > 0:
        upsert_holidays(holidays)

    cur.close()
    return None


def upsert_events(events: List[Dict[str, Any]], access_time: datetime.datetime, room_code: str = None, mnr: int = None):
    cur = db.cursor()

    courses = {}
    rows_insert = []
    rows_update = []
    holidays = []
    for evt in events:
        classes = evt['className'].split(' ')
        if classes[0] == 'holiday':
            holidays.append({
                'name': evt['title'],
                'start': tucal.parse_iso_timestamp(evt['start'], True).date(),
                'end': tucal.parse_iso_timestamp(evt['end'], True).date(),
            })
            continue

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
        data['course'] = data['name'] in courses and courses[data['name']] or get_course(data['name'])
        courses[data['name']] = data['course']

        cur.execute("""
            SELECT event_nr FROM tiss.event
            WHERE (room_code IS NULL OR %(room)s IS NULL OR COALESCE(room_code, '') = COALESCE(%(room)s, '')) AND
            (type, name, start_ts, end_ts, course_nr) = (%(type)s, %(name)s, %(start)s, %(end)s, %(course)s)""", data)
        event_nrs = cur.fetch_all()

        if len(event_nrs) > 0:
            data['nr'] = event_nrs[0][0]
            rows_update.append(data)
        else:
            rows_insert.append(data)

    if len(rows_update) > 0:
        cur.execute_values("""
            UPDATE tiss.event
            SET type = d.type, start_ts = d.start_ts, end_ts = d.end_ts, access_ts = d.access, name = d.name,
                livestream = d.live, online_only = d.online, course_nr = d.course
            FROM (VALUES (%(nr)s, %(type)s, %(start)s, %(end)s, %(access)s, %(name)s, %(live)s, %(online)s, %(course)s))
                 AS d (nr, type, start_ts, end_ts, access, name, live, online, course)
            WHERE event_nr = d.nr""", rows_update)
        if room_code is not None:
            cur.execute_values("UPDATE tiss.event SET room_code = %(room)s WHERE event_nr = %(nr)s", rows_update)

    inserted = []
    if len(rows_insert) > 0:
        cur.execute_values("""
            INSERT INTO tiss.event (type, room_code, start_ts, end_ts, access_ts, name, description,
                                    livestream, online_only, course_nr)
            VALUES (%(type)s, %(room)s, %(start)s, %(end)s, %(access)s, %(name)s, NULL, %(live)s, %(online)s,
                    %(course)s)
            RETURNING event_nr""", rows_insert)
        inserted = cur.fetch_all()
    evt_nrs = inserted + [evt['nr'] for evt in rows_update]

    if mnr and len(evt_nrs) > 0:
        cur.execute_values("""
            INSERT INTO tiss.event_user (event_nr, mnr) 
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING""", [(evt, mnr) for evt in evt_nrs])

    if len(holidays) > 0:
        upsert_holidays(holidays)

    cur.close()
    return None


def upsert_group_events(events: List[Dict[str, Any]], group: Dict[str, Any], course: Course,
                        access_time: datetime.datetime, mnr: int = None):
    cur = tucal.db.cursor()
    rows_insert = []
    rows_update = []
    for evt in events:
        name = f'{course.nr[:3]}.{course.nr[3:]} {course.type} {course.name_de} - {group["name"]}'
        data = {
            'name': name,
            'type': 2,
            'cnr': course.nr,
            'sem': str(course.semester),
            'start': evt['start'],
            'end': evt['end'],
            'room': evt['room_code'],
            'group_name': group['name'],
            'loc': evt['location'],
            'desc': evt['comment'],
            'acc': access_time,
        }
        cur.execute("""
            SELECT event_nr FROM tiss.event
            WHERE (room_code IS NULL OR %(room)s IS NULL OR COALESCE(room_code, '') = COALESCE(%(room)s, '')) AND
                  (type, name, start_ts, end_ts, course_nr) =
                  (%(type)s, %(name)s, %(start)s, %(end)s, %(cnr)s)""", data)
        matching = cur.fetch_all()
        if len(matching) > 0:
            data['nr'] = matching[0][0]
            rows_update.append(data)
        else:
            rows_insert.append(data)

    if len(rows_update) > 0:
        cur.execute_values("""
            UPDATE tiss.event e
            SET group_name = d.group_name, location = d.location, description = d.description, access_ts = d.acc,
                semester = d.sem, room_code = d.room
            FROM (VALUES (%(nr)s, %(group_name)s, %(loc)s, %(desc)s, %(acc)s, %(sem)s, %(room)s)) AS
                d (event_nr, group_name, location, description, acc, sem, room)
            WHERE e.event_nr = d.event_nr""", rows_update)

    inserted = []
    if len(rows_insert) > 0:
        cur.execute_values("""
            INSERT INTO tiss.event (type, course_nr, semester, room_code, group_name, start_ts, end_ts, access_ts, name,
                                    description, location)
            VALUES (%(type)s, %(cnr)s, %(sem)s, %(room)s, %(group_name)s, %(start)s, %(end)s, %(acc)s, %(name)s,
                    %(desc)s, %(loc)s)
            RETURNING event_nr""", rows_insert)
        inserted = cur.fetch_all()
    evt_nrs = inserted + [evt['nr'] for evt in rows_update]

    if mnr and len(evt_nrs) > 0:
        cur.execute_values("""
            INSERT INTO tiss.event_user (event_nr, mnr)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING""", [(evt, mnr) for evt in evt_nrs])

    cur.close()
    return None


def upsert_course_events(events: List[Dict[str, Any]], course: Course, access_time: datetime.datetime, mnr: int = None):
    cur = tucal.db.cursor()
    rows_insert = []
    rows_update = []
    for evt in events:
        data = {
            'name': f'{course.nr[:3]}.{course.nr[-3:]} {course.type} {course.name_de}',
            'type': 1,
            'cnr': course.nr,
            'sem': str(course.semester),
            'start': evt['start'],
            'end': evt['end'],
            'room': evt['room_code'],
            'loc': evt['location'],
            'desc': evt['comment'],
            'acc': access_time,
        }
        cur.execute("""
            SELECT event_nr FROM tiss.event
            WHERE (room_code IS NULL OR %(room)s IS NULL OR COALESCE(room_code, '') = COALESCE(%(room)s, '')) AND
                  (type, name, start_ts, end_ts, course_nr) =
                  (%(type)s, %(name)s, %(start)s, %(end)s, %(cnr)s)""", data)
        matching = cur.fetch_all()
        if len(matching) > 0:
            data['nr'] = matching[0][0]
            rows_update.append(data)
        else:
            rows_insert.append(data)

    if len(rows_update) > 0:
        cur.execute_values("""
            UPDATE tiss.event e
            SET location = d.location, description = d.description, access_ts = d.acc, semester = d.sem
            FROM (VALUES (%(nr)s, %(loc)s, %(desc)s, %(acc)s, %(sem)s)) AS
                d (event_nr, location, description, acc, sem)
            WHERE e.event_nr = d.event_nr""", rows_update)

    inserted = []
    if len(rows_insert) > 0:
        cur.execute_values("""
            INSERT INTO tiss.event (type, course_nr, semester, room_code, start_ts, end_ts, access_ts, name,
                description, location)
            VALUES (%(type)s, %(cnr)s, %(sem)s, %(room)s, %(start)s, %(end)s, %(acc)s, %(name)s,
                %(desc)s, %(loc)s)
            RETURNING event_nr""", rows_insert)
        inserted = cur.fetch_all()
    evt_nrs = inserted + [evt['nr'] for evt in rows_update]

    if mnr and len(evt_nrs) > 0:
        cur.execute_values("""
            INSERT INTO tiss.event_user (event_nr, mnr)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING""", [(evt, mnr) for evt in evt_nrs])

    cur.close()
    return None
