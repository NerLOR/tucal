#!/bin/env python3

import argparse

import tucal.db
import tuwien.tiss

AREAS = '../data/areas.csv'
BUILDINGS = '../data/buildings.csv'
ROOMS = '../data/rooms.csv'
COURSE_ACRONYMS = '../data/course_acronyms.csv'
LECTURE_TUBE = '../data/lecture_tube.csv'

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
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            data = {heading[n]: row[n] for n in range(len(heading))}
            data['type'] = mapping[data['type']]
            data['nr'] = counters[data['type']]
            counters[data['type']] += 1

            room_codes = data['room_codes'].split(' ')
            if len(room_codes) > 1:
                for rc in room_codes:
                    if room_codes[0][:2] != rc[:2]:
                        raise RuntimeError(f'Invalid room codes for room "{data["name"]}": {room_codes}')
            data['area_id'] = room_codes[0][0]
            data['building'] = room_codes[0][1]

            cur.execute("""
                INSERT INTO tucal.room (room_nr, area_id, building_id, tiss_code, room_name, room_suffix,
                    room_name_short, room_alt_name, area, capacity)
                VALUES (%(nr)s, %(area_id)s, %(building)s, %(tiss_code)s, %(name)s, %(suffix)s, %(name_short)s,
                    %(alt_name)s, %(area)s, %(capacity)s)""", data)

            for rc in room_codes:
                cur.execute("INSERT INTO tucal.room_location (room_nr, floor_nr, local_code) VALUES (%s, %s, %s)",
                            (data['nr'], rc[2:4], rc[4:]))

    with open(LECTURE_TUBE) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            data = {heading[n]: row[n] for n in range(len(heading))}
            data['floor'] = data['room_code'][2:4]
            data['local'] = data['room_code'][4:]
            cur.execute("""
                INSERT INTO tucal.lecture_tube (room_nr, floor_nr, local_code, lt_name)
                VALUES ((SELECT room_nr FROM tucal.v_room 
                         WHERE room_code LIKE CONCAT('%%', %(room_code)s, '%%')), 
                    %(floor)s, %(local)s, %(name)s)""", data)

    s = tuwien.tiss.Session()
    for room in s.rooms.values():
        data = {
            'id': room.id,
            'name': room.name,
            'full': room.tiss_name,
        }
        cur.execute("""
            INSERT INTO tiss.room (code, name, name_full)
            VALUES (%(id)s, %(name)s, %(full)s)
            ON CONFLICT ON CONSTRAINT pk_room DO
            UPDATE SET name = %(name)s, name_full = %(full)s""", data)
    cur.close()
    tucal.db.commit()
