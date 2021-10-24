
import requests
import re
import typing

TUWIEN_URL = 'https://www.tuwien.at'
GUT_URI = '/tu-wien/organisation/zentrale-bereiche/gebaeude-und-technik'
RDB_URI = f'{GUT_URI}/veranstaltungsservice/raumdatenbank'
RDB_URL = f'{TUWIEN_URL}{RDB_URI}'


class Room:
    building_id: str
    floor_nr: str
    room_nr: str
    name: str
    type: str
    area: typing.Optional[int]

    def __init__(self, room_id: str, name: str, room_type: str, area: typing.Optional[float]):
        parts = room_id.split(' ')
        if len(parts) == 1:
            parts = [room_id[0:2], room_id[2:4], room_id[4:]]
        elif len(parts) == 2:
            parts = [room_id[0:2], room_id[2:4], parts[1]]
        self.building_id = parts[0]
        self.floor_nr = parts[1]
        self.room_nr = parts[2]
        self.name = name
        self.type = room_type
        self.area = int(area) if area else None

    @property
    def id(self) -> str:
        return f'{self.building_id} {self.floor_nr} {self.room_nr}'

    def __str__(self) -> str:
        return f'<Room#{self.id}{{{self.name}}}>'

    def __repr__(self) -> str:
        return f'<Room#{self.id}{{{self.name};{self.type};{self.area}}}>'


def get_rooms() -> [Room]:
    s = requests.Session()
    rooms = []
    r = s.get(RDB_URL)
    categories = list({link.group(1) for link in re.finditer(rf'<a href="{RDB_URI}/([^/"]+)"', r.text)})
    categories.sort()
    for cat in categories:
        r = s.get(f'{RDB_URL}/{cat}')
        room_names = [link.group(1) for link in re.finditer(rf'<a href="{RDB_URI}/{cat}/([^/"]+)"', r.text)]
        for room in room_names:
            r = s.get(f'{RDB_URL}/{cat}/{room}')
            data = {
                link.group(1).strip().lower(): re.sub(r'<.*?>', '', link.group(2).strip().replace('&nbsp;', ''))
                for link in re.finditer(r'<p><strong>(.*?):.*?</strong>(.*?)</p>', r.text)
            }
            name = next(re.finditer(r'<h1>(.*?)</h1>', r.text)).group(1).strip()
            name = name.replace('Seminaraum', 'Seminarraum')
            if 'raumcode' not in data:
                continue
            rooms.append(Room(
                data['raumcode'],
                name,
                data.get('raumtyp'),
                float(data['fläche'].split(' ')[0].split('m')[0].replace(',', '.')) if 'fläche' in data else None
            ))
    return rooms
