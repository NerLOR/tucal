#!/bin/env python3

import re
import typing
import sys

import tuwien.tiss
import tuwien.colab
import tuwien.rdb

NAME_REPLACE = re.compile(r'[^A-Za-z0-9äüößÄÜÖẞ]')


class Room:
    name: str
    suffix: typing.Optional[str]
    name_short: typing.Optional[str]
    alt_name: typing.Optional[str]
    room_codes: [str]
    tiss_code: typing.Optional[str]
    type: typing.Optional[str]
    parent_name: typing.Optional[str]
    area: typing.Optional[int]
    capacity: typing.Optional[int]
    comment: typing.Optional[str]

    def __init__(self, name: str, room_code: str, tiss_code: str = None, room_type: str = None,
                 area: int = None, capacity: int = None, comment: str = None):
        self.name = re.sub(r' *- +[A-Z-]*$', '', name.split(' - Achtung!')[0]).split(' - mündl.')[0].replace(',', '')
        self.name = self.name.replace('HS', 'Hörsaal')
        self.name = self.name\
            .replace('Sem.R.', 'Seminarraum')\
            .replace('Sem. R.', 'Seminarraum')\
            .replace('Sem.', 'Seminarraum')\
            .replace('Sem ', 'Seminarraum ')
        self.name = self.name.replace('AI', 'Atominstitut')
        self.suffix = None
        self.name_short = None
        self.alt_name = None
        self.room_codes = [room_code.replace(' ', '')]
        self.tiss_code = tiss_code
        self.type = room_type
        if self.type is None:
            if 'hörsaal' in self.name.lower() or 'Audi. Max.' in self.name or 'Atrium' in self.name:
                self.type = 'lecture_hall'
            elif 'seminarraum' in self.name.lower():
                self.type = 'seminar_room'
            elif 'projektraum' in self.name.lower():
                self.type = 'project_room'
            elif 'lab' in self.name.lower():
                self.type = 'lab'
            elif 'zeichensaal' in self.name.lower():
                self.type = 'drawing_room'
            elif 'büro' in self.name.lower():
                self.type = 'office'
            elif self.name.startswith('PC') or self.name.startswith('EDV') or self.name.startswith('CAD'):
                self.type = 'lab'
        self.parent_name = None
        self.area = area
        self.capacity = capacity
        self.comment = comment


if __name__ == '__main__':
    print('Fetching coLAB rooms...', file=sys.stderr)
    colab_rooms = [
        Room(room.name, room.id, comment='colab')
        for room in tuwien.colab.get_rooms()
    ]
    print('Successfully fetched coLAB rooms', file=sys.stderr)

    print('Fetching TISS rooms...', file=sys.stderr)
    s = tuwien.tiss.Session()
    tiss_rooms = [
        Room(room.name, room.global_id, tiss_code=room.id, capacity=room.capacity, comment='tiss')
        for room in s.rooms.values()
    ]
    print('Successfully fetched TISS rooms', file=sys.stderr)

    print('Fetching RDB rooms...', file=sys.stderr)
    rdb_rooms = [
        Room(room.name, room.id, room_type=room.type, area=room.area, comment='rdb')
        for room in tuwien.rdb.get_rooms()
    ]
    print('Successfully fetched RDB rooms', file=sys.stderr)

    print('Processing rooms...', file=sys.stderr)
    rooms: [Room] = colab_rooms + tiss_rooms + rdb_rooms
    rooms.sort(key=lambda room: (room.room_codes[0][0] + NAME_REPLACE.sub('', room.name)).lower())

    proc = [rooms[0]]
    for room in rooms[1:]:
        last = proc[-1]
        ln = NAME_REPLACE.sub('', last.name.split('|')[0].lower())
        rn = NAME_REPLACE.sub('', room.name.lower())
        if last.room_codes[0] == room.room_codes[0] and (room.tiss_code is None or last.tiss_code is None) and \
                (ln.startswith(rn) or rn.startswith(ln)):
            last.area = last.area or room.area
            last.capacity = last.capacity or room.capacity
            last.tiss_code = last.tiss_code or room.tiss_code
            last.comment = last.comment + ' ' + room.comment
            if last.name != room.name:
                last.name = last.name + ' | ' + room.name
            last.type = last.type or room.type
            if last.type != room.type and (last.type is not None and room.type is not None):
                if room.name == 'Aufbaulabor':
                    last.type = 'drawing_room'
        else:
            proc.append(room)
    proc.sort(
        key=lambda room:
        ((room.type or "other")[:3] +
         room.room_codes[0][0] +
         re.sub(r'[0-9]+', lambda m: ('0000' + m.group(0))[-4:], NAME_REPLACE.sub('', room.name))
         ).lower()
    )
    print('Finished processing rooms', file=sys.stderr)

    print('name,suffix,name_short,alt_name,room_codes,tiss_code,type,parent_name,area,capacity,comment')
    for room in proc:
        print(f'{room.name},{room.suffix or ""},{room.name_short or ""},{room.alt_name or ""},'
              f'{" ".join(room.room_codes)},{room.tiss_code or ""},{room.type or "other"},{room.parent_name or ""},'
              f'{room.area or ""},{room.capacity or ""},{room.comment or ""}')
