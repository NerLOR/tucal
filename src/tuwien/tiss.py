
from __future__ import annotations
import random
import typing
import requests
import re
import datetime
import html

from tucal import Semester
import tucal.icalendar
import tuwien.sso

TISS_DOMAIN = 'tiss.tuwien.ac.at'
TISS_URL = f'https://{TISS_DOMAIN}'

OPTION_BUILDING = re.compile(r'<option value="([A-Z]+)".*?>([A-Z]+) - (.*?) \(([^()]*?)\)</option>')
OPTION_ROOM = re.compile(r'<option value="([^"]+)"[^>]*>(.*?)( \(([0-9]+)\))?</option>')
OPTION_INSTITUTE = re.compile(r'<option value="(E[0-9]{3}[^"]*)">(.*?)</option>')

COURSE_TITLE = re.compile(r'<h1>[^<>]*<span[^>]*>[^<>]*</span>\s*(.*?)\s*<', re.MULTILINE | re.UNICODE)
COURSE_META = re.compile(r'<div id="subHeader" class="clearfix">'
                         r'[0-9SW]+, ([A-Z]+), ([0-9]+\.[0-9]+)h, ([0-9]+\.[0-9]+)EC')

CDATA = re.compile(r'<!\[CDATA\[(.*?)]]>')
UPDATE_VIEW_STATE = re.compile(r'<update id="j_id__v_0:javax.faces.ViewState:1"><!\[CDATA\[(.*?)]]></update>')
INPUT_VIEW_STATE = re.compile(r'<input.*?name="javax\.faces\.ViewState".*?value="([^"]*)".*?/>')
TABLE_TR = re.compile(r'<tr.*?>(.*?)</tr>')
TABLE_TD = re.compile(r'<td.*?>(.*?)</td>')
TAGS = re.compile(r'<.*?>')
SPACES = re.compile(r'\s+')


def iso_to_datetime(iso_str: str) -> (datetime.datetime, datetime.timezone):
    td = datetime.timedelta(hours=int(iso_str[-4:-3]), minutes=int(iso_str[-2:-1]))
    if iso_str[-5] == '-':
        td = -td
    tz = datetime.timezone(td)
    dt = datetime.datetime.fromisoformat(iso_str[:19])
    return dt, tz


class Building:
    id: str
    name: str
    tiss_name: str
    address: typing.Optional[str]
    _global_rooms: typing.Dict[str, Room]

    def __init__(self, building_id: str, tiss_name: str, name: typing.Optional[str] = None,
                 address: typing.Optional[str] = None, global_rooms: typing.Dict[str, Room] = None):
        self.id = building_id
        self.tiss_name = tiss_name
        self.name = name or tiss_name
        self.address = address if address is None or len(address) > 0 else None
        self._global_rooms = global_rooms

    @property
    def rooms(self) -> [Room]:
        return [room for room in self._global_rooms.values() if room.building.id == self.id]

    def __str__(self) -> str:
        return f'<Building#{self.id}{{{self.name}}}>'

    def __repr__(self) -> str:
        return f'<Building#{self.id}{{{self.name};{self.address};{self.tiss_name}}}>'


class Room:
    id: str
    name: str
    tiss_name: str
    capacity: typing.Optional[int]
    global_id: typing.Optional[str]
    _building_id: str
    _global_buildings: typing.Dict[str, Building]

    def __init__(self, room_id: str, building_id: str, tiss_name: str, name: typing.Optional[str] = None,
                 capacity: typing.Optional[int] = None, global_buildings: {str: Building} = None):
        self.id = room_id
        self.tiss_name = tiss_name
        self.name = name or tiss_name.split(' - Achtung!')[0]
        self._building_id = building_id
        self.capacity = capacity
        self._global_buildings = global_buildings
        self.global_id = None

    @property
    def building(self) -> Building:
        if self._global_buildings is None:
            raise RuntimeError('_global_buildings not initialized')
        return self._global_buildings[self._building_id]

    def __str__(self) -> str:
        return f'<Room#{self.id}{{{self._building_id},{self.name}}}>'

    def __repr__(self) -> str:
        return f'<Room#{self.id}{{{self._building_id},{self.name},{self.capacity},{self.tiss_name}}}>'


class Course:
    nr: str
    semester: Semester
    name_de: str
    name_en: str
    type: str
    ects: float

    def __init__(self, nr: str, semester: Semester, name_de: str, name_en: str, course_type: str, ects: float):
        self.nr = nr
        self.semester = Semester(str(semester))
        self.name_de = name_de
        self.name_en = name_en
        self.type = course_type
        self.ects = ects

    def __str__(self) -> str:
        return f'<Course#{self.nr[:3]}.{self.nr[-3:]}-{self.semester}{{{self.type},{self.name_de},{self.ects}}}>'

    def __repr__(self) -> str:
        return f'<Course#{self.nr}-{self.semester}{{{self.type},{self.name_de},{self.name_en},{self.ects}}}>'


class Event:
    id: str
    start: datetime.datetime
    end: datetime.datetime
    all_day: bool
    title: str
    description: typing.Optional[str]
    type: str
    room: Room

    def __init__(self, event_id: str, start: datetime.datetime, end: datetime.datetime, title: str, event_type: str,
                 room: Room, description: typing.Optional[str] = None, all_day: bool = False):
        self.id = event_id.replace('.', '')
        self.start = start
        self.end = end
        self.title = title
        self.type = event_type
        self.description = description
        self.all_day = all_day
        self.room = room

    @staticmethod
    def from_json_obj(obj: typing.Dict[str], room: Room) -> Event:
        return Event(obj['id'], iso_to_datetime(obj['start'])[0], iso_to_datetime(obj['end'])[0], obj['title'],
                     obj['className'], room, obj['allDay'])


class Session:
    _win_id: int
    _req_token: int
    _view_state: typing.Optional[str]
    _session: requests.Session
    _sso: tuwien.sso.Session
    _buildings: typing.Optional[typing.Dict[str, Building]]
    _rooms: typing.Optional[typing.Dict[str, Room]]
    _courses: typing.Optional[typing.Dict[str, Course]]

    def __init__(self, session: tuwien.sso.Session = None):
        self._win_id = Session.gen_win_id()
        self._req_token = Session.gen_req_token()
        self._buildings = None
        self._rooms = None
        self._courses = None
        self._view_state = None
        self._session = session and session.session or requests.Session()
        self._sso = session
        self._session.cookies.set(f'dsrwid-{self._req_token}', f'{self._win_id}', domain=TISS_DOMAIN)
        self._session.cookies.set('TISS_LANG', 'de', domain=TISS_DOMAIN)

    @staticmethod
    def gen_req_token() -> int:
        return random.randint(0, 999)

    @staticmethod
    def gen_win_id() -> int:
        return random.randint(1000, 9999)

    def update_endpoint(self, endpoint: str) -> str:
        endpoint += '&' if '?' in endpoint else '?'
        endpoint += f'dswid={self._win_id}&dsrid={self._req_token}'
        if endpoint[0] != '/':
            endpoint = f'/{endpoint}'
        return endpoint

    def _update_view_state(self, text: str, ajax: bool = False):
        pattern = UPDATE_VIEW_STATE if ajax else INPUT_VIEW_STATE
        for update in pattern.finditer(text):
            self._view_state = update.group(1)

    def get(self, endpoint: str, headers: typing.Dict[str, object] = None,
            allow_redirects: bool = True) -> requests.Response:
        r = self._session.get(f'{TISS_URL}{self.update_endpoint(endpoint)}', headers=headers,
                              allow_redirects=allow_redirects)
        self._update_view_state(r.text)
        return r

    def post(self, endpoint: str, data: typing.Dict[str, object],
             headers: typing.Dict[str, object] = None, ajax: bool = False) -> requests.Response:
        headers = headers or {}
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'

        data['javax.faces.ClientWindow'] = self._win_id
        data['dspwid'] = self._win_id

        if ajax:
            data['javax.faces.partial.ajax'] = 'true'
            data['X-Requested-With'] = 'XMLHttpRequest'
            data['Faces-Request'] = 'partial/ajax'

        if self._view_state is not None:
            data['javax.faces.ViewState'] = self._view_state
        elif 'javax.faces.ViewState' in data:
            del data['javax.faces.ViewState']

        r = self._session.post(f'{TISS_URL}{endpoint}', data=data, headers=headers)
        self._update_view_state(r.text, ajax=ajax)

        return r

    def sso_login(self) -> bool:
        if self._sso is None:
            raise RuntimeError('No SSO session provided')
        return self._sso.login(f'{TISS_URL}/admin/authentifizierung')

    def _get_buildings(self) -> [Building]:
        r = self.get('/events/selectRoom.xhtml')
        return [
            Building(opt.group(2), opt.group(3), address=opt.group(4), global_rooms=self._rooms)
            for opt in OPTION_BUILDING.finditer(r.text)
        ]

    def _get_rooms_for_building(self, building: Building) -> [Room]:
        data = {
            'filterForm:roomFilter:selectBuildingLb': building.id,
            'javax.faces.behavior.event': 'valueChange',
            'javax.faces.partial.event': 'change',
            'javax.faces.source': 'filterForm:roomFilter:selectBuildingLb',
            'javax.faces.partial.execute': 'filterForm:roomFilter',
            'javax.faces.partial.render': 'filterForm:roomFilter',
        }

        # Retrieve view_state
        self._view_state = None
        self.post('/events/selectRoom.xhtml', data, ajax=True)

        r = self.post('/events/selectRoom.xhtml', data, ajax=True)
        rooms = [
            Room(option.group(1), building.id, tiss_name=option.group(2), global_buildings=self._buildings)
            for option in OPTION_ROOM.finditer(r.text[r.text.find('filterForm:roomFilter:selectRoomLb'):])
        ]

        for room in rooms:
            self._get_room_details(room)

        return rooms

    def _get_room_details(self, room: Room):
        data = {
            'filterForm:roomFilter:selectBuildingLb': room.building.id,
            'filterForm:roomFilter:selectRoomLb': room.id,
            'javax.faces.behavior.event': 'action',
            'javax.faces.partial.event': 'click',
            'javax.faces.source': 'filterForm:roomFilter:searchButton',
            'javax.faces.partial.execute': 'filterForm:roomFilter filterForm:roomFilter:searchButton',
            'javax.faces.partial.render': 'filterForm tableForm',
        }

        # Retrieve view_state
        self._view_state = None
        self.post('/events/selectRoom.xhtml', data, ajax=True)

        r = self.post('/events/selectRoom.xhtml', data, ajax=True)
        for tr in TABLE_TR.finditer(r.text):
            row = [TAGS.sub('', td.group(1)) for td in TABLE_TD.finditer(tr.group(1))]
            if len(row) == 0:
                continue
            room.global_id = row[-1].strip().replace(' ', '')
            if room.global_id == '':
                room.global_id = room.id
            room.capacity = int(row[1].strip())

    def _get_course(self, course_nr: str, semester: Semester) -> Course:
        course_nr = course_nr.replace('.', '')

        r = self.get(f'/course/courseDetails.xhtml?courseNr={course_nr}&semester={semester}&locale=de')
        title_de = html.unescape(COURSE_TITLE.findall(r.text)[0].strip())
        meta = COURSE_META.findall(r.text)[0]

        r = self.get(f'/course/courseDetails.xhtml?courseNr={course_nr}&semester={semester}&locale=en')
        title_en = html.unescape(COURSE_TITLE.findall(r.text)[0].strip())

        course_type = meta[0]
        ects = meta[2]

        return Course(course_nr, semester, title_de, title_en, course_type, ects)

    def course_generator(self, semester: Semester, semester_to: Semester = None,
                         skip: typing.Set[(str, Semester)] = None) -> typing.Generator[Course]:
        skip = skip or set()

        data1 = {
            'javax.faces.source': 'courseList:j_id_2g',
            'javax.faces.partial.execute': 'courseList:searchField',
            'javax.faces.partial.render': 'courseList globalMessagesPanel',
            'javax.faces.behavior.event': 'action',
            'javax.faces.partial.event': 'click',
        }
        self.post('/course/courseList.xhtml', data1, ajax=True)
        r = self.post('/course/courseList.xhtml', data1, ajax=True)

        institutes = [opt.group(1) for opt in OPTION_INSTITUTE.finditer(r.text)]
        course_nrs = set()
        for institute in institutes:
            data = {
                'courseList:institutes': institute,
                'courseList_SUBMIT': '1',
                'courseList:semFrom': semester,
                'courseList:semTo': semester_to or semester,
                'courseList:cSearchBtn': 'Suchen',
            }
            self._view_state = None
            self.get('/course/courseList.xhtml')
            self.post('/course/courseList.xhtml', data1, ajax=True)
            r = self.post('/course/courseList.xhtml', data)
            for tr in TABLE_TR.finditer(r.text):
                row = [td.group(1) for td in TABLE_TD.finditer(tr.group(0))]
                if len(row) > 0:
                    course_nrs.add((row[0].replace('.', ''), Semester(row[5])))

        for course in course_nrs - skip:
            yield self._get_course(course[0], course[1])

    def _get_courses(self, semester: Semester, semester_to: Semester = None) -> typing.Dict[str, Course]:
        return {
            f'{course.nr}-{course.semester}': course
            for course in self.course_generator(semester, semester_to)
        }

    @property
    def buildings(self) -> typing.Dict[str, Building]:
        if self._buildings is None:
            self._buildings = {}
            for building in self._get_buildings():
                self._buildings[building.id] = building
        return self._buildings

    @property
    def rooms(self) -> typing.Dict[str, Room]:
        if self._rooms is None:
            self._rooms = {}
            for building in self.buildings.values():
                for room in self._get_rooms_for_building(building):
                    self._rooms[room.id] = room
        return self._rooms

    @property
    def courses(self) -> typing.Dict[str, Course]:
        if self._courses is None:
            self._courses = self._get_courses(Semester.last(), Semester.current())
        return self._courses

    def get_event_course(self, event_id: int, course_nr: str) -> (typing.Optional[str], typing.Optional[Semester]):
        r = self.get(f'/education/goToEvent.xhtml?id={course_nr}-{event_id}&type=EXAM',
                     allow_redirects=False)
        print(r.status_code, r.request.url)
        print(r.headers['Location'])
        'https://tiss.tuwien.ac.at/education/goToEvent.xhtml?id=188999-4503954&type=EXAM'
        'https://tiss.tuwien.ac.at/education/goToEvent.xhtml?id=188999-393157&type=EXAM'

        return None, None

    def get_room_schedule(self, room_code: str) -> tucal.icalendar.Calendar:
        r = self._session.get(f'{TISS_URL}/events/rest/calendar/room?locale=de&roomCode={room_code}')
        cal = tucal.icalendar.parse_ical(r.text)
        return cal
