#!/bin/env python3

import argparse

import tucal.db
import tuwien.tiss

AREAS = '../data/areas.csv'
BUILDINGS = '../data/buildings.csv'
ROOMS = '../data/rooms.csv'
COURSE_ACRONYMS = '../data/course_acronyms.csv'

EVENT_TYPES = '../data/tiss/event_types.csv'
COURSE_TYPES = '../data/tiss/course_types.csv'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    cur = tucal.db.cursor()

    with open(EVENT_TYPES) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            data = {heading[n]: row[n] for n in range(len(heading))}
            cur.execute("""
                INSERT INTO tiss.event_type (type, name_de, name_en)
                VALUES (%(nr)s, %(name_de)s, %(name_en)s)
                ON CONFLICT ON CONSTRAINT pk_event_type DO
                UPDATE SET name_de = %(name_de)s, name_en = %(name_en)s""", data)

    with open(COURSE_TYPES) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            data = {heading[n]: row[n] for n in range(len(heading))}
            cur.execute("""
                INSERT INTO tiss.course_type (type, name_de, name_en)
                VALUES (%(code)s, %(name_de)s, %(name_en)s)
                ON CONFLICT ON CONSTRAINT pk_course_type DO
                UPDATE SET name_de = %(name_de)s, name_en = %(name_en)s""", data)

    with open(COURSE_ACRONYMS) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            data = {heading[n]: row[n] for n in range(len(heading))}
            cur.execute("""
                INSERT INTO tucal.course_acronym (course_nr, program, short, acronym_1, acronym_2)
                VALUES (%(nr)s, %(program)s, %(short)s, %(acronym_1)s, %(acronym_2)s)
                ON CONFLICT ON CONSTRAINT pk_course_acronym DO
                UPDATE SET program = %(program)s, short = %(short)s, acronym_1 = %(acronym_1)s,
                    acronym_2 = %(acronym_2)s""", data)

    with open(AREAS) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            data = {heading[n]: row[n] for n in range(len(heading))}
            data['in_use'] = data['in_use'] == 'yes'
            cur.execute("""
                INSERT INTO tucal.area (area_id, area_name, area_suffix, in_use)
                VALUES (%(area_id)s, %(name)s, %(suffix)s, %(in_use)s)
                ON CONFLICT ON CONSTRAINT pk_area DO
                UPDATE SET area_name = %(name)s, area_suffix = %(suffix)s, in_use = %(in_use)s""", data)

    with open(BUILDINGS) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            data = {heading[n]: row[n] for n in range(len(heading))}
            cur.execute("""
                INSERT INTO tucal.building (area_id, local_id, building_name, building_suffix, building_alt_name,
                    object_nr, address)
                VALUES (%(area_id)s, %(building_id)s, %(name)s, %(suffix)s, %(alt_name)s, %(object_nr)s, %(address)s)
                ON CONFLICT ON CONSTRAINT pk_building DO
                UPDATE SET building_name = %(name)s, building_suffix = %(suffix)s, building_alt_name = %(alt_name)s,
                object_nr = %(object_nr)s, address = %(address)s""", data)

    tucal.db.commit()

    with open(ROOMS) as f:
        counters = {
            'lecture_hall': 1001,
            'seminar_room': 2001,
            'lab': 3001,
            'other': 4001,
            'event_room': 9001,
        }
        mapping = {
            'circulation_area': 'event_room',
            'drawing_room': 'seminar_room',
            'event_room': 'event_room',
            'lab': 'lab',
            'lecture_hall': 'lecture_hall',
            'office': 'other',
            'other': 'other',
            'project_room': 'seminar_room',
            'seminar_room': 'seminar_room',
        }
        f.readline()
        for line in f.readlines():
            data = [d.strip() for d in line.strip().split(',')]
            t = mapping[data[6]]
            r_nr = counters[t]
            counters[t] += 1

            r_name = data[0] if len(data[0]) > 0 else None
            r_suffix = data[1] if len(data[1]) > 0 else None
            r_short = data[2] if len(data[2]) > 0 else None
            r_alt = data[3] if len(data[3]) > 0 else None
            r_area = int(data[8]) if len(data[8]) > 0 else None
            r_cap = int(data[9]) if len(data[9]) > 0 else None
            r_tiss = data[5] if len(data[5]) > 0 else None
            room_codes = data[4].split(' ')
            if len(room_codes) > 1:
                for rc in room_codes:
                    if room_codes[0][:2] != rc[:2]:
                        raise RuntimeError(f'Invalid room codes for room "{r_name}": {room_codes}')
            a_id = data[4][0]
            b_id = data[4][1]

            cur.execute("INSERT INTO tucal.room (room_nr, area_id, building_id, tiss_code, room_name, room_suffix, "
                        "room_name_short, room_alt_name, area, capacity) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ",
                        (r_nr, a_id, b_id, r_tiss, r_name, r_suffix, r_short, r_alt, r_area, r_cap))

            for rc in room_codes:
                cur.execute("INSERT INTO tucal.room_location (room_nr, floor_nr, local_code) VALUES (%s, %s, %s)",
                            (r_nr, rc[2:4], rc[4:]))

    s = tuwien.tiss.Session()
    for room in s.rooms.values():
        cur.execute("INSERT INTO tiss.room (code, name, name_full) "
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT ON CONSTRAINT pk_room DO UPDATE SET name = %s, name_full = %s",
                    (room.id, room.name, room.tiss_name, room.name, room.tiss_name))
    cur.close()
    tucal.db.commit()
