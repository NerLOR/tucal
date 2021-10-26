#!/bin/env python3

import psycopg2

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
