
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

    print('Updating event types...')
    rows = []
    with open(EVENT_TYPES) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            rows.append({heading[n]: int(row[n]) if heading[n] == 'nr' else row[n] for n in range(len(heading))})
    fields = {'type': 'nr', 'name_de': 'name_de', 'name_en': 'name_en'}
    tucal.db.upsert_values('tiss.event_type', rows, fields, ('type',))
    print('Updated event types')

    print('Updating course types...')
    rows = []
    with open(COURSE_TYPES) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            rows.append({heading[n]: row[n] for n in range(len(heading))})
    fields = {'type': 'code', 'name_de': 'name_de', 'name_en': 'name_en'}
    tucal.db.upsert_values('tiss.course_type', rows, fields, ('type',))
    print('Updated course types')

    print('Updating course acronyms...')
    rows = []
    with open(COURSE_ACRONYMS) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            rows.append({heading[n]: row[n] for n in range(len(heading))})
    fields = {
        'course_nr': 'nr',
        'program': 'program',
        'short': 'short',
        'acronym_1': 'acronym_1',
        'acronym_2': 'acronym_2',
    }
    tucal.db.upsert_values('tucal.course_acronym', rows, fields, ('course_nr',))
    print('Updated course acronyms')

    print('Updating areas...')
    rows = []
    with open(AREAS) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            data = {heading[n]: row[n] for n in range(len(heading))}
            data['in_use'] = data['in_use'] == 'yes'
            rows.append(data)
    fields = {'area_id': 'area_id', 'area_name': 'name', 'area_suffix': 'suffix', 'in_use': 'in_use'}
    tucal.db.upsert_values('tucal.area', rows, fields, ('area_id',))
    print('Updated areas')

    print('Updating buildings...')
    rows = []
    with open(BUILDINGS) as f:
        heading = [d.strip() for d in f.readline().strip().split(',')]
        for line in f.readlines():
            row = [d.strip() if len(d.strip()) > 0 else None for d in line.strip().split(',')]
            rows.append({
                heading[n]: int(row[n]) if heading[n] == 'object_nr' and row[n] else row[n]
                for n in range(len(heading))
            })
    fields = {
        'area_id': 'area_id',
        'local_id': 'building_id',
        'building_name': 'name',
        'building_suffix': 'suffix',
        'building_alt_name': 'alt_name',
        'object_nr': 'object_nr',
        'address': 'address',
    }
    tucal.db.upsert_values('tucal.building', rows, fields, ('area_id', 'local_id'))
    print('Updated buildings')

    tucal.db.commit()

    print('Fetching tiss rooms...')
    s = tuwien.tiss.Session()
    rows = [{
        'id': room.id,
        'name': room.name,
        'full': room.tiss_name,
    } for room in s.rooms.values()]

    fields = {'code': 'id', 'name': 'name', 'name_full': 'full'}
    tucal.db.upsert_values('tiss.room', rows, fields, ('code',))
    print('Updated tiss rooms')

    tucal.db.commit()

    print('Updating rooms...')
    cur = tucal.db.cursor()
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
    cur.close()
    print('Updated rooms')

    tucal.db.commit()
