#!/bin/env python3

import re

from tucal import Semester
import tucal.db
import tuwien.tiss

COURSE = re.compile(r'^([0-9]{3}\.[0-9A-Z]{3})')

CATEGORY_TYPES = {
    'OTHER': 0,
    'COURSE': 1,
    'GROUP': 2,
    'EXAM': 3,
    'ORG': 4,
    'LEARN_SLOT': 5,
}


if __name__ == '__main__':
    s = tuwien.tiss.Session()

    cur = tucal.db.cursor()

    cur.execute("SELECT course_nr, semester FROM tiss.course")
    courses = cur.fetchall()

    cur.execute("SELECT code FROM tiss.room")
    for code, in cur.fetchall():
        cal = s.get_room_schedule(code)
        for evt in cal.events:
            evt_id = int(evt.uid.split('@')[0].split('-')[1])
            evt_type = CATEGORY_TYPES[evt.categories[0]]
            name = evt.summary

            course, semester = None, Semester.from_date(evt.start)
            for c in COURSE.finditer(evt.summary):
                course = c.group(1).replace('.', '')

            if evt.categories[0] == 'EXAM':
                course, semester = None, None

            sem = str(semester)
            if course is not None and sem is not None and (course, sem) not in courses:
                if (course, str(semester + 1)) in courses:
                    sem = str(semester + 1)
                elif (course, str(semester - 1)) in courses:
                    sem = str(semester - 1)
                else:
                    print(f'Course not in db: {code}, {evt.start}, {name}')
                    course, sem = None, None

            cur.execute("INSERT INTO tiss.event (event_id, event_uid, type, course_nr, semester, room_code, start_ts, "
                        "end_ts, access_ts, name, description) "
                        "VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                        "ON CONFLICT ON CONSTRAINT sk_event_id "
                        "DO UPDATE SET type = %s, course_nr = %s, semester = %s, room_code = %s, start_ts = %s, "
                        "end_ts = %s, access_ts = %s, name = %s, description = %s",
                        (evt_id, evt_type, course, sem, code, evt.start, evt.end, evt.access, name, evt.description,
                         evt_type, course, sem, code, evt.start, evt.end, evt.access, name, evt.description))
    cur.close()
    tucal.db.commit()

