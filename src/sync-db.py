#!/bin/env python3

import psycopg2

import tuwien.tiss

AREAS = '../data/areas.csv'
BUILDINGS = '../data/buildings.csv'
ROOMS = '../data/rooms.csv'


if __name__ == '__main__':
    db: psycopg2._psycopg.connection = psycopg2.connect(
        "dbname=tucal user=necronda host=data.necronda.net password=Password123"
    )
    cur: psycopg2._psycopg.cursor = db.cursor()

    with open(AREAS) as f:
        f.readline()
        for line in f.readlines():
            data = [d.strip() for d in line.strip().split(',')]
            a_id = data[0]
            a_name = data[1] if len(data[1]) > 0 else None
            a_suffix = data[2] if len(data[2]) > 0 else None
            in_use = data[3] == 'yes'
            cur.execute("INSERT INTO area (area_id, area_name, area_suffix, in_use) "
                        "VALUES (%s, %s, %s, %s) "
                        "ON CONFLICT (area_id) DO "
                        "UPDATE SET area_name = %s, area_suffix = %s, in_use = %s",
                        (a_id, a_name, a_suffix, in_use, a_name, a_suffix, in_use))

    with open(BUILDINGS) as f:
        f.readline()
        for line in f.readlines():
            data = [d.strip() for d in line.strip().split(',')]
            a_id = data[0]
            b_id = data[1]
            b_name = data[2] if len(data[2]) > 0 else None
            b_suffix = data[3] if len(data[3]) > 0 else None
            b_alt_name = data[4] if len(data[4]) > 0 else None
            b_obj = data[5] if len(data[5]) > 0 else None
            b_address = data[6] if len(data[6]) > 0 else None
            cur.execute("INSERT INTO building "
                        "(area_id, local_id, building_name, building_suffix, building_alt_name, object_nr, address) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (area_id, local_id) DO "
                        "UPDATE SET building_name = %s, building_suffix = %s, building_alt_name = %s, object_nr = %s, "
                        "address = %s",
                        (a_id, b_id, b_name, b_suffix, b_alt_name, b_obj, b_address, b_name, b_suffix, b_alt_name,
                         b_obj, b_address))

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

            cur.execute("INSERT INTO room (room_nr, area_id, building_id, tiss_code, room_name, room_suffix, "
                        "room_name_short, room_alt_name, area, capacity) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ",
                        (r_nr, a_id, b_id, r_tiss, r_name, r_suffix, r_short, r_alt, r_area, r_cap))

            for rc in room_codes:
                cur.execute("INSERT INTO room_location (room_nr, floor_nr, local_code) VALUES (%s, %s, %s)",
                            (r_nr, rc[2:4], rc[4:]))

    s = tuwien.tiss.Session()
    for room in s.rooms.values():
        cur.execute("UPDATE room SET tiss_name = %s, tiss_name_full = %s WHERE tiss_code = %s",
                    (room.name, room.tiss_name, room.id))
    db.commit()
