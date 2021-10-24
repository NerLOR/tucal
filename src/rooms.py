#!/bin/env python3

import tuwien.tiss
import tuwien.colab
import tuwien.rdb
import psycopg2
import re

AREAS = '../data/areas.csv'
BUILDINGS = '../data/buildings.csv'


def buildings(cur: psycopg2._psycopg.cursor):
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
            b_address = data[5] if len(data[5]) > 0 else None
            cur.execute("INSERT INTO building "
                        "(area_id, local_id, building_name, building_suffix, building_alt_name, address) "
                        "VALUES (%s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (area_id, local_id) DO "
                        "UPDATE SET building_name = %s, building_suffix = %s, building_alt_name = %s, address = %s",
                        (a_id, b_id, b_name, b_suffix, b_alt_name, b_address, b_name, b_suffix, b_alt_name, b_address))


if __name__ == '__main__':
    db: psycopg2._psycopg.connection = psycopg2.connect(
        "dbname=tucal user=necronda host=data.necronda.net password=..."
    )
    cur: psycopg2._psycopg.cursor = db.cursor()

    buildings(cur)
    db.commit()

    rdb_rooms = tuwien.rdb.get_rooms()
    for r in rdb_rooms:
        print(r)
        cur.execute("INSERT INTO room (room_name, area) "
                    "VALUES (%s, %s) "
                    "ON CONFLICT (room_name) DO "
                    "UPDATE SET area = %s "
                    "RETURNING room_nr",
                    (r.name, r.area, r.area))
        rnr = cur.fetchall()[0]
        cur.execute("INSERT INTO room_location (room_nr, area_id, building_id, floor_nr, local_code) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT ON CONSTRAINT pk_room_location DO NOTHING",
                    (rnr, r.building_id[0], r.building_id[1], r.floor_nr, r.room_nr))
    db.commit()

    s = tuwien.tiss.Session()
    for r in s.rooms.values():
        print(r)
        a_id = r.global_id[0:1]
        b_id = r.global_id[1:2]
        f_nr = r.global_id[2:4]
        l_nr = r.global_id[4:]
        name = r.name.split(' - Achtung!')[0]
        name = re.sub(r' *- +[A-Z-]*$', '', name)
        name = name.split(' - mündl.')[0]
        cur.execute("INSERT INTO tiss_room "
                    "(area_id, building_id, floor_nr, local_code, tiss_code, room_name, tiss_name, capacity) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT ON CONSTRAINT pk_tiss_room DO "
                    "UPDATE SET tiss_code = %s, room_name = %s, tiss_name = %s, capacity = %s",
                    (a_id, b_id, f_nr, l_nr, r.id, name, r.name, r.capacity, r.id, name, r.name, r.capacity))
    db.commit()
