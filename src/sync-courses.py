#!/bin/env python3

import sys
import json
import os

from tucal import Semester
import tucal.db
import tuwien.tiss

TEMP_FILE = '/tmp/tucal-courses.json'


if __name__ == '__main__':
    courses = []

    if os.path.isfile(TEMP_FILE):
        with open(TEMP_FILE, 'r') as f:
            for line in f.readlines():
                if len(line.strip()) > 0:
                    data = json.loads(line)
                    courses.append(tuwien.tiss.Course(**data))

    print(f'Found {len(courses)} entries in temp file', file=sys.stderr)

    s = tuwien.tiss.Session()
    with open(TEMP_FILE, 'a') as f:
        skip = {(c.nr, c.semester) for c in courses}
        for c in s.course_generator(Semester.last(), Semester.next(), skip=skip):
            print(c, file=sys.stderr)
            courses.append(c)
            print(json.dumps({
                'nr': c.nr,
                'semester': str(c.semester),
                'course_type': c.type,
                'name_de': c.name_de,
                'name_en': c.name_en,
                'ects': c.ects,
            }), file=f)

    cur = tucal.db.cursor()
    for c in courses:
        cur.execute("INSERT INTO tiss.course (course_nr, semester, name_de, name_en, type, ects) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT ON CONSTRAINT pk_course "
                    "DO UPDATE SET name_de = %s, name_en = %s, type = %s, ects = %s",
                    (c.nr, str(c.semester), c.name_de, c.name_en, c.type, c.ects, c.name_de, c.name_en, c.type, c.ects))
    cur.close()
    tucal.db.commit()

    os.remove(TEMP_FILE)
