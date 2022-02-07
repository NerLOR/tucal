
from typing import Optional
import requests
import re
import html

COLAB_URL = 'https://colab.tuwien.ac.at'
TABLE = re.compile(r'<table.*?>(.*?)</table>')
TR = re.compile(r'<tr>(.*?)</tr>')
TD = re.compile(r'<td.*?>(.*?)</td>')


class Room:
    id: str
    name: str
    building: Optional[str]

    def __init__(self, room_id: str, name: str, building: Optional[str]):
        self.id = room_id
        self.name = name.replace('Semianrraum', 'Seminarraum')
        self.building = building

    def __repr__(self):
        return f'<Room#{self.id}{{{self.name},{self.building}}}>'

    def __str__(self):
        return f'<Room#{self.id}{{{self.name}}}>'


def get_rooms() -> [Room]:
    r = requests.get(f'{COLAB_URL}/display/ROOMINFO/Rauminformation', verify=False)
    rooms = []
    for table in TABLE.finditer(r.text):
        for tr in TR.finditer(table.group(1)):
            data = [
                html.unescape(re.sub(r'</?(span|div|p).*?>', '', td.group(1)).replace('&nbsp;', ''))
                for td in TD.finditer(tr.group(1))
            ]
            if len(data) == 0:
                continue
            bez = re.sub(r'<.*?>', '', data[0]).split(',', 1)
            rooms.append(Room(data[1].replace(' ', ''), bez[-1].strip(), bez[0].strip() if len(bez) > 1 else None))
    return rooms
