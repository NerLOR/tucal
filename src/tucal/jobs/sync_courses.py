
import json
import os
import argparse

from tucal import Semester, Job
import tucal.db
import tuwien.tiss

TEMP_FILE = '/tmp/tucal-courses.json'

TISS_INIT_VAL = 100
DB_VAL = 10


def sync_courses(keep_file: bool = False, job: Job = None):
    job = job or Job()
    job.init('sync courses', 3)

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
        job.perc_steps[-1] = TISS_INIT_VAL + n + DB_VAL
        job.end(TISS_INIT_VAL)
        job.begin('get tiss courses', n)
        for c_nr, c_sem, cb in gen:
            job.begin(f'get tiss course {c_nr}-{c_sem}')
            c = cb()
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
    rows = [{
        'nr': c.nr,
        'de': c.name_de,
        'en': c.name_en,
        'type': c.type,
        'sem': str(c.semester),
        'ects': c.ects,
    } for c in courses]
    fields = {'course_nr': 'nr', 'name_de': 'de', 'name_en': 'en', 'type': 'type'}
    tucal.db.upsert_values('tiss.course_def', rows, fields, ('course_nr',))
    fields = {'course_nr': 'nr', 'semester': 'sem', 'ects': 'ects'}
    tucal.db.upsert_values('tiss.course', rows, fields, ('course_nr', 'semester'))

    tucal.db.commit()
    job.end(DB_VAL)

    if not keep_file:
        os.remove(TEMP_FILE)

    job.end(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--keep', '-k', action='store_true', default=False)
    args = parser.parse_args()
    sync_courses(keep_file=args.keep)
