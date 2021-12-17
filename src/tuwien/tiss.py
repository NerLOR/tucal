
from __future__ import annotations
import random
import typing
import requests
import re
import datetime
import time
import html
import json

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
LINK_TOKEN = re.compile(rf'<a href="{TISS_URL}/events/rest/calendar/personal\?[^"]*?token=([^"]*)">Download</a>')
LINK_SUBSCRIPTION = re.compile(r'<a href="/education/subscriptionSettings\.xhtml\?sgId=([^"]*)"')
INPUT_CHECKBOX = re.compile(r'<input id="([^"]*)" type="checkbox" name="([^"]*)"( checked="([^"]*)")?')
LINK_COURSE = re.compile(r'<a href="/course/educationDetails\.xhtml\?'
                         r'semester=([0-9WS]+)&amp;courseNr=([A-Z0-9]+)">([^<]*)</a>')
SPAN_BOLD = re.compile(r'<span class="bold">\s*(.*?)\s*</span>', re.MULTILINE | re.DOTALL)
GROUP_OL_LI = re.compile(r'<li>\s*<label[^>]*>\s*(.*?)\s*</label>\s*<span[^>]*>\s*(.*?)\s*</span>\s*</li>')
ROOM_CODE = re.compile(r'roomCode=([^/&]*)')

TABLE_TR = re.compile(r'<tr[^>]*>\s*(.*?)\s*</tr>', re.MULTILINE | re.DOTALL)
TABLE_TD = re.compile(r'<td[^>]*>\s*(.*?)\s*</td>', re.MULTILINE | re.DOTALL)
GROUP_DIV = re.compile(r'<div class="groupWrapper">(.*?)</fieldset>', re.MULTILINE | re.DOTALL)

TAGS = re.compile(r'<script[^>]*>.*?</script>|<[^>]*>', re.MULTILINE | re.DOTALL)
SPACES = re.compile(r'\s+')


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
        self.nr = nr.replace('.', '')
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
        start = tucal.parse_iso_timestamp(obj['start'], True)
        end = tucal.parse_iso_timestamp(obj['end'], True)
        return Event(obj['id'], start, end, obj['title'], obj['className'], room, obj['allDay'])


class Session:
    _win_id: int
    _req_token: int
    _view_state: typing.Optional[str]
    _session: requests.Session
    _sso: tuwien.sso.Session
    _buildings: typing.Optional[typing.Dict[str, Building]]
    _rooms: typing.Optional[typing.Dict[str, Room]]
    _courses: typing.Optional[typing.Dict[str, Course]]
    _calendar_token: typing.Optional[str]
    _favorites = typing.Optional[typing.List[Course]]
    _timeout: float

    def __init__(self, session: tuwien.sso.Session = None, timeout: float = 20):
        self._win_id = Session.gen_win_id()
        self._req_token = Session.gen_req_token()
        self._timeout = timeout
        self._buildings = None
        self._rooms = None
        self._courses = None
        self._view_state = None
        self._calendar_token = None
        self._favorites = None
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
                              allow_redirects=allow_redirects, timeout=self._timeout)
        self._update_view_state(r.text)
        return r

    def post(self, endpoint: str, data: typing.Dict[str, object], headers: typing.Dict[str, object] = None,
             ajax: bool = False, allow_redirects: bool = True) -> requests.Response:
        headers = headers or {}
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'

        data['javax.faces.ClientWindow'] = self._win_id
        data['dspwid'] = self._win_id

        if ajax:
            headers['X-Requested-With'] = 'XMLHttpRequest'
            headers['Faces-Request'] = 'partial/ajax'
            data['javax.faces.partial.ajax'] = 'true'

        if self._view_state is not None:
            data['javax.faces.ViewState'] = self._view_state
        elif 'javax.faces.ViewState' in data:
            del data['javax.faces.ViewState']

        r = self._session.post(f'{TISS_URL}{endpoint}', data=data, headers=headers,
                               timeout=self._timeout, allow_redirects=allow_redirects)
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
                         skip: typing.Set[(str, Semester)] = None) -> typing.Generator[Course or int]:
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
                row = [td.group(1) for td in TABLE_TD.finditer(tr.group(1))]
                if len(row) > 0:
                    course_nrs.add((row[0].replace('.', ''), Semester(row[5])))

        yield len(course_nrs)
        for course in course_nrs - skip:
            yield course[0], course[1], lambda: self._get_course(course[0], course[1])

    def _get_courses(self, semester: Semester, semester_to: Semester = None) -> typing.Dict[str, Course]:
        gen = self.course_generator(semester, semester_to)
        next(gen)
        return {
            f'{course.nr}-{course.semester}': course
            for course in gen
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

    def get_room_schedule_ical(self, room_code: str) -> typing.Optional[tucal.icalendar.Calendar]:
        r = self._session.get(f'{TISS_URL}/events/rest/calendar/room?locale=de&roomCode={room_code}',
                              timeout=self._timeout, allow_redirects=False)
        if r.status_code == 200:
            return tucal.icalendar.parse_ical(r.text)
        else:
            return None

    def get_room_schedule(self, room_code: str) -> typing.Dict[str, typing.Any]:
        data = {
            'javax.faces.partial.execute': 'calendarForm:schedule',
            'javax.faces.partial.render': 'calendarForm:schedule',
            'calendarForm:schedule': 'calendarForm:schedule',
            'calendarForm:schedule_start': int(time.mktime(tucal.Semester.last().first_day.timetuple()) * 1000),
            'calendarForm:schedule_end': int(time.mktime(tucal.Semester.next().last_day.timetuple()) * 1000),
        }
        self.get(f'/events/roomSchedule.xhtml?roomCode={room_code.replace(" ", "+")}')
        r = self.post('/events/roomSchedule.xhtml', data, ajax=True)
        for cdata in CDATA.finditer(r.text):
            cd = cdata.group(1)
            if cd.startswith('{') and cd.endswith('}'):
                return json.loads(cd)

    def get_personal_schedule_ical(self, token: str) -> typing.Optional[tucal.icalendar.Calendar]:
        r = self._session.get(f'{TISS_URL}/events/rest/calendar/personal?locale=de&token={token}',
                              timeout=self._timeout, allow_redirects=False)
        if r.status_code == 200:
            return tucal.icalendar.parse_ical(r.text)
        else:
            return None

    def get_personal_schedule(self) -> typing.Dict[str, typing.Any]:
        data = {
            'javax.faces.partial.execute': 'calendarForm:schedule',
            'javax.faces.partial.render': 'calendarForm:schedule',
            'calendarForm:schedule': 'calendarForm:schedule',
            'calendarForm:schedule_start': int(time.mktime(tucal.Semester.last().first_day.timetuple()) * 1000),
            'calendarForm:schedule_end': int(time.mktime(tucal.Semester.next().last_day.timetuple()) * 1000),
        }
        self.get('/events/personSchedule.xhtml')
        r = self.post('/events/personSchedule.xhtml', data, ajax=True)
        for cdata in CDATA.finditer(r.text):
            cd = cdata.group(1)
            if cd.startswith('{') and cd.endswith('}'):
                return json.loads(cd)

    def _get_calendar_token(self) -> str:
        r = self.get('/events/personSchedule.xhtml')
        for link in LINK_TOKEN.finditer(r.text):
            return link.group(1)

        # Fallback. generate new token
        data = {
            'javax.faces.behavior.event': 'action',
            'javax.faces.partial.event': 'click',
            'javax.faces.source': 'j_id_7g:j_id_7h_8',
            'javax.faces.partial.execute': 'j_id_7g:j_id_7h_8',
            'javax.faces.partial.render': 'j_id_7g globalMessagesPanel',
            'j_id_7g_SUBMIT': '1',
        }
        r = self.post('/events/personSchedule.xhtml', data, ajax=True)
        for link in LINK_TOKEN.finditer(r.text):
            return link.group(1)

        raise RuntimeError('can not find calendar token')

    @property
    def calendar_token(self) -> str:
        if self._calendar_token is None:
            self._calendar_token = self._get_calendar_token()
        return self._calendar_token

    def update_calendar_settings(self):
        r = self.get('/education/favorites.xhtml')

        subs = [link.group(1) for link in LINK_SUBSCRIPTION.finditer(r.text)]
        for sub in subs:
            r = self.get(f'/education/subscriptionSettings.xhtml?sgId={sub}')
            data = {
                'settings:updateBtn': 'Speichern',
                'settings_SUBMIT': '1',
            }
            for box in INPUT_CHECKBOX.finditer(r.text):
                if box.group(4) == 'checked':
                    data[box.group(1)] = 'true'

            if data.get('settings:eventOption', None) == 'true':
                continue
            else:
                data['settings:eventOption'] = 'true'

            self.post('/education/subscriptionSettings.xhtml', data)

    @property
    def favorites(self) -> typing.List[Course]:
        if self._favorites is None:
            self._favorites = self._get_favorites()
        return self._favorites

    def _get_favorites(self) -> typing.List[Course]:
        r = self.get('/education/favorites.xhtml')
        courses = []
        for row in TABLE_TR.finditer(r.text):
            data = [d.group(1) for d in TABLE_TD.finditer(row.group(1))][1:4]
            if len(data) != 3 or data[0] == 'Summe':
                continue
            course = LINK_COURSE.findall(data[0])[0]
            courses.append(Course(course[1], course[0], course[2], None, None, float(data[2])))
        return courses

    def get_groups(self, course: Course) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        r = self.get(f'/education/course/groupList.xhtml?semester={course.semester}&courseNr={course.nr}')
        groups = {}
        for g_html in GROUP_DIV.finditer(r.text):
            text = g_html.group(1).strip()
            name, status = SPAN_BOLD.findall(text)
            data = {a: b for a, b in GROUP_OL_LI.findall(text)}
            enrolled = (status == 'angemeldet')

            appl_start = datetime.datetime.strptime(
                data['Beginn der Anmeldung'], '%d.%m.%Y, %H:%M') if 'Beginn der Anmeldung' in data else None
            appl_end = datetime.datetime.strptime(
                data['Ende der Anmeldung'], '%d.%m.%Y, %H:%M') if 'Ende der Anmeldung' in data else None
            dereg_end = datetime.datetime.strptime(
                data['Ende der Online-Abmeldung'], '%d.%m.%Y, %H:%M') if 'Ende der Online-Abmeldung' in data else None
            groups[name] = {
                'name': name,
                'enrolled': enrolled,
                'application_start': appl_start,
                'application_end': appl_end,
                'deregistration_end': dereg_end,
                'events': []
            }
            for row in TABLE_TR.finditer(text):
                event = [d.group(1) for d in TABLE_TD.finditer(row.group(1))]
                if len(event) == 0:
                    continue
                date, start_time, end_time, location, comment = event
                m = ROOM_CODE.findall(location)
                room_code = None
                if len(m) > 0:
                    room_code = m[0]

                iso_date = '-'.join(date.split('.')[::-1])
                start = tucal.parse_iso_timestamp(f'{iso_date}T{start_time}:00', True)
                end = tucal.parse_iso_timestamp(f'{iso_date}T{end_time}:00', True)

                groups[name]['events'].append({
                    'location': location if not room_code else None,
                    'room_code': room_code,
                    'comment': comment,
                    'group': name,
                    'start': start,
                    'end': end,
                })
        return groups

    def get_course_events(self, course: Course):
        r = self.get(f'/course/educationDetails.xhtml?semester={course.semester}&courseNr={course.nr}')
