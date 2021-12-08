
import json
import os
import argparse

from tucal import Semester, Job
import tucal.db
import tuwien.tiss

TEMP_FILE = '/tmp/tucal-courses.json'

TISS_INIT_VAL = 100
DB_VAL = 10


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--keep', '-k', action='store_true', default=False)
    args = parser.parse_args()

    job = Job('sync courses', 3)

    courses = []
    if os.path.isfile(TEMP_FILE):
        with open(TEMP_FILE, 'r') as f:
            for line in f.readlines():
                if len(line.strip()) > 0:
                    data = json.loads(line)
                    courses.append(tuwien.tiss.Course(**data))

    print(f'Found {len(courses)} entries in temp file')

    job.begin('get tiss institutes')
    s = tuwien.tiss.Session()
    with open(TEMP_FILE, 'a') as f:
        skip = {(c.nr, c.semester) for c in courses}
        gen = s.course_generator(Semester.current() - 2, Semester.current() + 1, skip=skip)
        n = next(gen) - len(skip)
        job.perc_steps = TISS_INIT_VAL + n + DB_VAL
        job.end(TISS_INIT_VAL)
        job.begin('get tiss courses', n)
        for c in gen:
            job.begin(f'get tiss course {c.nr}-{c.semester} {c.type} {c.name_de}')
            courses.append(c)
            print(json.dumps({
                'nr': c.nr,
                'semester': str(c.semester),
                'course_type': c.type,
                'name_de': c.name_de,
                'name_en': c.name_en,
                'ects': c.ects,
            }), file=f)
            job.end(1)
    job.end(0)

    job.begin('update database')
    cur = tucal.db.cursor()
    for c in courses:
        data = {
            'nr': c.nr,
            'de': c.name_de,
            'en': c.name_en,
            'type': c.type,
            'sem': str(c.semester),
            'ects': c.ects,
        }
        cur.execute("""
            INSERT INTO tiss.course_def (course_nr, name_de, name_en, type)
            VALUES (%(nr)s, %(de)s, %(en)s, %(type)s)
            ON CONFLICT ON CONSTRAINT pk_course_def
            DO UPDATE SET name_de = %(de)s, name_en = %(en)s, type = %(type)s""", data)
        cur.execute("""
            INSERT INTO tiss.course (course_nr, semester, ects)
            VALUES (%(nr)s, %(sem)s, %(ects)s)
            ON CONFLICT ON CONSTRAINT pk_course
            DO UPDATE SET ects = %(ects)s""", data)
    cur.close()
    tucal.db.commit()
    job.end(DB_VAL)

    if not args.keep:
        os.remove(TEMP_FILE)

    job.end(0)
