
from __future__ import annotations
from typing import List, Dict, Any, Optional, Set, Generator
import random
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
OPTION_SEMESTER = re.compile(r'<option value="([0-9]{4}[WS])">\1</option>')

COURSE_TITLE = re.compile(r'<h1>[^<>]*<span[^>]*>[^<>]*</span>\s*(.*?)\s*<', re.MULTILINE | re.UNICODE)
COURSE_META = re.compile(r'<div id="subHeader" class="clearfix">'
                         r'[0-9SW]+, ([A-Z]+), ([0-9]+\.[0-9]+)h, ([0-9]+\.[0-9]+)EC')

CDATA = re.compile(r'<!\[CDATA\[(.*?)]]>')
UPDATE_VIEW_STATE = re.compile(r'<update id="j_id__v_0:jakarta\.faces\.ViewState:1"><!\[CDATA\[(.*?)]]></update>')
INPUT_VIEW_STATE = re.compile(r'<input.*?name="jakarta\.faces\.ViewState".*?value="([^"]*)".*?/>')
LINK_TOKEN = re.compile(rf'<a href="{TISS_URL}/events/rest/calendar/personal\?[^"]*?token=([^"]*)">Download</a>')
LINK_SUBSCRIPTION = re.compile(r'<a href="/education/subscriptionSettings\.xhtml\?sgId=([^"]*)"')
INPUT_CHECKBOX = re.compile(r'<input id="([^"]*)" type="checkbox" name="([^"]*)"( checked="([^"]*)")?')
LINK_COURSE = re.compile(r'<a href="/course/educationDetails\.xhtml\?'
                         r'semester=([0-9WS]+)&amp;courseNr=([A-Z0-9]+)">([^<]*)</a>')
SPAN_TYPE = re.compile(r'<span title="Typ">, ([A-Z]+), </span>')
SPAN_BOLD = re.compile(r'<span class="bold">\s*(.*?)\s*</span>', re.MULTILINE | re.DOTALL)
GROUP_OL_LI = re.compile(r'<li>\s*<label[^>]*>\s*(.*?)\s*</label>\s*<span[^>]*>\s*(.*?)\s*</span>\s*</li>')
ROOM_CODE = re.compile(r'roomCode=([^/&]*)')

TABLE_TR = re.compile(r'<tr[^>]*>\s*(.*?)\s*</tr>', re.MULTILINE | re.DOTALL)
TABLE_TD = re.compile(r'<td[^>]*>\s*(.*?)\s*</td>', re.MULTILINE | re.DOTALL)
GROUP_DIV = re.compile(r'<div class="groupWrapper">(.*?)</fieldset>', re.MULTILINE | re.DOTALL)

EVENT_TABLE = re.compile(r'<div.*?id=".*?:eventTable".*?</table>')

TAGS = re.compile(r'<script[^>]*>.*?</script>|<[^>]*>', re.MULTILINE | re.DOTALL)
SPACES = re.compile(r'\s+')

LI_BEGIN = re.compile(r'<span id="registrationForm:begin">(.*?)</span>')
LI_END = re.compile(r'<span id="registrationForm:end">(.*?)</span>')
LI_DEREGEND = re.compile(r'<span id="registrationForm:deregEnd">(.*?)</span>')
LI_APP_BEGIN = re.compile(r'<span id="groupContentForm:.*?:appBeginn">(.*?)</span>')
LI_APP_END = re.compile(r'<span id="groupContentForm:.*?:appEnd">(.*?)</span>')
DIV_EXAM = re.compile(r'<div class="groupWrapper">(.*?)groupHeadertrigger"><span class="bold">\s*([^<>]*)\s*'
                      r'</span>([^<>]*)\n(.*?)<div class="header_element"><span class="bold">\s*([^<>]*?)\s*</span>'
                      r'(.*?)</fieldset>', re.MULTILINE | re.DOTALL)
LABEL_EXAM = re.compile(r'<li><label for="examDateListForm:[^"]*">([^<>]*)</label><span[^>]*>(.*?)</li>',
                        re.MULTILINE | re.DOTALL)

BUTTON_EVENTS = re.compile(r'<a.*?id="(.*?):(.*?)"[^>]*>Einzeltermine anzeigen</a>')
BUTTON_SEARCH = re.compile(r'<a.*?id="courseList:(.*?)"[^>]*>Erweiterte Suche</a>')
BUTTON_TOKEN = re.compile(r'<input.*?id="(.*?):(.*?)".*?value="Erzeuge neuen Token"')
BUTTON_EXAM = re.compile(r'<a.*?id="examDateListForm:(.*?)"[^>]*>Alle Prüfungen')


class Building:
    id: str
    name: str
    tiss_name: str
    address: Optional[str]
    _global_rooms: Dict[str, Room]

    def __init__(self, building_id: str, tiss_name: str, name: Optional[str] = None,
                 address: Optional[str] = None, global_rooms: Dict[str, Room] = None):
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
    capacity: Optional[int]
    global_id: Optional[str]
    _building_id: str
    _global_buildings: Dict[str, Building]

    def __init__(self, room_id: str, building_id: str, tiss_name: str, name: Optional[str] = None,
                 capacity: Optional[int] = None, global_buildings: {str: Building} = None):
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
        return f'<Course#{self.nr[:3]}.{self.nr[3:]}-{self.semester}{{{self.type},{self.name_de},{self.ects}}}>'

    def __repr__(self) -> str:
        return f'<Course#{self.nr}-{self.semester}{{{self.type},{self.name_de},{self.name_en},{self.ects}}}>'


class Event:
    id: str
    start: datetime.datetime
    end: datetime.datetime
    all_day: bool
    title: str
    description: Optional[str]
    type: str
    room: Room

    def __init__(self, event_id: str, start: datetime.datetime, end: datetime.datetime, title: str, event_type: str,
                 room: Room, description: Optional[str] = None, all_day: bool = False):
        self.id = event_id.replace('.', '')
        self.start = start
        self.end = end
        self.title = title
        self.type = event_type
        self.description = description
        self.all_day = all_day
        self.room = room

    @staticmethod
    def from_json_obj(obj: Dict[str], room: Room) -> Event:
        start = tucal.parse_iso_timestamp(obj['start'], True)
        end = tucal.parse_iso_timestamp(obj['end'], True)
        return Event(obj['id'], start, end, obj['title'], obj['className'], room, obj['allDay'])


class Session:
    _win_id: int
    _req_token: int
    _view_state: Optional[str]
    _session: requests.Session
    _sso: tuwien.sso.Session
    _buildings: Optional[Dict[str, Building]]
    _rooms: Optional[Dict[str, Room]]
    _courses: Optional[Dict[str, Course]]
    _calendar_token: Optional[str]
    _favorites = Optional[List[Course]]
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

    def get(self, endpoint: str, headers: Dict[str, object] = None,
            allow_redirects: bool = True) -> requests.Response:
        r = self._session.get(f'{TISS_URL}{self.update_endpoint(endpoint)}', headers=headers,
                              allow_redirects=allow_redirects, timeout=self._timeout)
        self._update_view_state(r.text)

        pos = r.url.find('errorCode=')
        if pos != -1:
            r.status_code = int(r.url[pos + 10:pos + 13])

        return r

    def post(self, endpoint: str, data: Dict[str, object], headers: Dict[str, object] = None,
             ajax: bool = False, allow_redirects: bool = True) -> requests.Response:
        headers = headers or {}
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'

        data['jakarta.faces.ClientWindow'] = self._win_id
        data['dspwid'] = self._win_id

        if ajax:
            headers['X-Requested-With'] = 'XMLHttpRequest'
            headers['Faces-Request'] = 'partial/ajax'
            data['jakarta.faces.partial.ajax'] = 'true'

        if self._view_state is not None:
            data['jakarta.faces.ViewState'] = self._view_state
        elif 'jakarta.faces.ViewState' in data:
            del data['jakarta.faces.ViewState']

        r = self._session.post(f'{TISS_URL}{endpoint}', data=data, headers=headers,
                               timeout=self._timeout, allow_redirects=allow_redirects)
        self._update_view_state(r.text, ajax=ajax)

        pos = r.url.find('errorCode=')
        if pos != -1:
            r.status_code = int(r.url[pos + 10:pos + 13])

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
            'jakarta.faces.behavior.event': 'valueChange',
            'jakarta.faces.partial.event': 'change',
            'jakarta.faces.source': 'filterForm:roomFilter:selectBuildingLb',
            'jakarta.faces.partial.execute': 'filterForm:roomFilter',
            'jakarta.faces.partial.render': 'filterForm:roomFilter',
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
            'jakarta.faces.behavior.event': 'action',
            'jakarta.faces.partial.event': 'click',
            'jakarta.faces.source': 'filterForm:roomFilter:searchButton',
            'jakarta.faces.partial.execute': 'filterForm:roomFilter filterForm:roomFilter:searchButton',
            'jakarta.faces.partial.render': 'filterForm tableForm',
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

    def get_course(self, course_nr: str, semester: Semester) -> Course:
        semester = Semester(str(semester))
        course_nr = course_nr.replace('.', '')

        r = self.get(f'/course/courseDetails.xhtml?courseNr={course_nr}&semester={semester}&locale=de')
        if r.status_code != 200:
            raise tucal.CourseNotFoundError()

        title_de = html.unescape(COURSE_TITLE.search(r.text).group(1).strip())
        meta = COURSE_META.search(r.text).groups()

        r = self.get(f'/course/courseDetails.xhtml?courseNr={course_nr}&semester={semester}&locale=en')
        if r.status_code != 200:
            raise tucal.CourseNotFoundError()

        title_en = html.unescape(COURSE_TITLE.search(r.text).group(1).strip())

        course_type = meta[0]
        ects = float(meta[2])

        return Course(course_nr, semester, title_de, title_en, course_type, ects)

    def course_generator(self, semester: Semester, semester_to: Semester = None,
                         skip: Set[(str, Semester)] = None) -> Generator[Course or int]:
        skip = skip or set()
        r = self.get('/course/courseList.xhtml')

        m = BUTTON_SEARCH.search(r.text)
        if not m:
            raise tucal.TissError()

        id_1 = m.group(1)
        data1 = {
            'jakarta.faces.source': f'courseList:{id_1}',
            'jakarta.faces.partial.execute': 'courseList:searchField',
            'jakarta.faces.partial.render': 'courseList globalMessagesPanel',
            'jakarta.faces.behavior.event': 'action',
            'jakarta.faces.partial.event': 'click',
        }
        r = self.post('/course/courseList.xhtml', data1, ajax=True)

        semesters = [Semester(opt.group(1)) for opt in OPTION_SEMESTER.finditer(r.text)]
        if semester_to > semesters[0]:
            semester_to = semesters[0]

        institutes = [opt.group(1) for opt in OPTION_INSTITUTE.finditer(r.text)]
        course_nrs = set()
        for sem in range(int(semester), int(semester_to) + 1):
            semester = Semester.from_int(sem)
            for institute in institutes:
                data = {
                    'courseList:institutes': institute,
                    'courseList_SUBMIT': '1',
                    'courseList:semFrom': str(semester),
                    'courseList:semTo': str(semester),
                    'courseList:cSearchBtn': 'Suchen',
                }
                self._view_state = None
                self.get('/course/courseList.xhtml')
                self.post('/course/courseList.xhtml', data1, ajax=True)
                r = self.post('/course/courseList.xhtml', data)
                if 'bitte verfeinern Sie Ihre Eingabe' in r.text:
                    raise RuntimeError('TISS search returned too many results')

                for tr in TABLE_TR.finditer(r.text):
                    row = [td.group(1) for td in TABLE_TD.finditer(tr.group(1))]
                    if len(row) > 0:
                        course_nrs.add((row[0].replace('.', ''), Semester(row[5])))

        # TODO yield course_nrs at the beginning
        yield len(course_nrs)
        for course in course_nrs - skip:
            yield course[0], course[1], lambda: self.get_course(course[0], course[1])

    def _get_courses(self, semester: Semester, semester_to: Semester = None) -> Dict[str, Course]:
        gen = self.course_generator(semester, semester_to)
        next(gen)
        return {
            f'{course.nr}-{course.semester}': course
            for course in gen
        }

    @property
    def buildings(self) -> Dict[str, Building]:
        if self._buildings is None:
            self._buildings = {}
            for building in self._get_buildings():
                self._buildings[building.id] = building
        return self._buildings

    @property
    def rooms(self) -> Dict[str, Room]:
        if self._rooms is None:
            self._rooms = {}
            for building in self.buildings.values():
                for room in self._get_rooms_for_building(building):
                    self._rooms[room.id] = room
        return self._rooms

    @property
    def courses(self) -> Dict[str, Course]:
        if self._courses is None:
            self._courses = self._get_courses(Semester.last(), Semester.current())
        return self._courses

    def get_room_schedule_ical(self, room_code: str) -> Optional[tucal.icalendar.Calendar]:
        r = self._session.get(f'{TISS_URL}/events/rest/calendar/room?locale=de&roomCode={room_code}',
                              timeout=self._timeout, allow_redirects=False)
        if r.status_code == 200:
            return tucal.icalendar.parse_ical(r.text)
        else:
            return None

    def get_room_schedule(self, room_code: str) -> Dict[str, Any]:
        data = {
            'jakarta.faces.partial.execute': 'calendarForm:schedule',
            'jakarta.faces.partial.render': 'calendarForm:schedule',
            'calendarForm:schedule': 'calendarForm:schedule',
            'calendarForm:schedule_start': int(time.mktime(tucal.Semester.last().first_day.timetuple()) * 1000),
            'calendarForm:schedule_end': int(time.mktime(tucal.Semester.next().last_day.timetuple()) * 1000),
        }
        r = self.get(f'/events/roomSchedule.xhtml?roomCode={room_code.replace(" ", "+")}')
        if r.status_code != 200:
            raise tucal.RoomNotFoundError()

        r = self.post('/events/roomSchedule.xhtml', data, ajax=True)
        for cdata in CDATA.finditer(r.text):
            cd = cdata.group(1)
            if cd.startswith('{') and cd.endswith('}'):
                return json.loads(cd)

    def get_personal_schedule_ical(self, token: str) -> Optional[tucal.icalendar.Calendar]:
        r = self._session.get(f'{TISS_URL}/events/rest/calendar/personal?locale=de&token={token}',
                              timeout=self._timeout, allow_redirects=False)
        if r.status_code == 200:
            return tucal.icalendar.parse_ical(r.text)
        else:
            return None

    def get_personal_schedule(self) -> Dict[str, Any]:
        data = {
            'jakarta.faces.partial.execute': 'calendarForm:schedule',
            'jakarta.faces.partial.render': 'calendarForm:schedule',
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

        m = BUTTON_TOKEN.search(r.text)
        if not m:
            raise tucal.TissError()

        id_1, id_2 = m.group(1), m.group(2)
        # Fallback. generate new token
        data = {
            'jakarta.faces.behavior.event': 'action',
            'jakarta.faces.partial.event': 'click',
            'jakarta.faces.source': f'{id_1}:{id_2}',
            'jakarta.faces.partial.execute': f'{id_1}:{id_2}',
            'jakarta.faces.partial.render': f'{id_1} globalMessagesPanel',
            f'{id_1}_SUBMIT': '1',
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
    def favorites(self) -> List[Course]:
        if self._favorites is None:
            self._favorites = self._get_favorites()
        return self._favorites

    def _get_favorites(self) -> List[Course]:
        r = self.get('/education/favorites.xhtml')
        courses = []
        for row in TABLE_TR.finditer(r.text):
            data = [d.group(1) for d in TABLE_TD.finditer(row.group(1))][1:8]
            if len(data) != 7 or data[0] == 'Summe' or data[6] != '':
                continue
            course = LINK_COURSE.search(data[0]).groups()
            course_type = SPAN_TYPE.search(data[0]).group(1)
            courses.append(Course(course[1], course[0], course[2], None, course_type, float(data[2])))
        return courses

    def get_groups(self, course: Course) -> Dict[str, Dict[str, Any]]:
        r = self.get(f'/education/course/groupList.xhtml?semester={course.semester}&courseNr={course.nr}')
        if r.status_code != 200:
            raise tucal.CourseNotFoundError()

        groups = {}
        for g_html in GROUP_DIV.finditer(r.text):
            text = g_html.group(1).strip()
            name, status = SPAN_BOLD.findall(text)
            name, status = html.unescape(name), html.unescape(status)
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
                    room_code = re.sub(r'%([0-9A-Za-z]{2})', lambda a: chr(int(a[1], 16)), m[0].replace('+', ' '))

                iso_date = '-'.join(date.split('.')[::-1])
                start = tucal.parse_iso_timestamp(f'{iso_date}T{start_time}:00', True)
                end = tucal.parse_iso_timestamp(f'{iso_date}T{end_time}:00', True)

                groups[name]['events'].append({
                    'location': html.unescape(location) if not room_code else None,
                    'room_code': room_code,
                    'comment': html.unescape(comment),
                    'group': name,
                    'start': start,
                    'end': end,
                })
        return groups

    def get_course_events(self, course: Course) -> List[Dict[str, Any]]:
        events = []
        r = self.get(f'/course/educationDetails.xhtml?semester={course.semester}&courseNr={course.nr}')
        if r.status_code != 200:
            raise tucal.CourseNotFoundError()

        def append_events(date, time_from_to, location, comment):
            room_m = ROOM_CODE.findall(location)
            room_code = None
            if len(room_m) > 0:
                room_code = re.sub(r'%([0-9A-Za-z]{2})', lambda a: chr(int(a[1], 16)), room_m[0].replace('+', ' '))

            start_time, end_time = time_from_to.split(' - ')
            iso_date = '-'.join(date.split('.')[::-1])
            start = tucal.parse_iso_timestamp(f'{iso_date}T{start_time}:00', True)
            end = tucal.parse_iso_timestamp(f'{iso_date}T{end_time}:00', True)

            events.append({
                'location': html.unescape(location) if not room_code else None,
                'room_code': room_code,
                'comment': html.unescape(comment) if comment else None,
                'start': start,
                'end': end,
            })

        m = BUTTON_EVENTS.search(r.text)
        if not m:
            table = EVENT_TABLE.search(r.text)
            if table is None:
                return[]

            for row in TABLE_TR.finditer(table.group(0)):
                event = [d.group(1) for d in TABLE_TD.finditer(row.group(1))]
                if len(event) == 0:
                    continue

                day, time_from_to, date, location = event[:4]
                comment = event[-1]
                append_events(date, time_from_to, location, comment)
            return events

        id_1, id_2 = m.group(1), m.group(2)
        data = {
            'jakarta.faces.source': f'{id_1}:{id_2}',
            'jakarta.faces.partial.execute': f'{id_1}:eventDetailDateTable',
            'jakarta.faces.partial.render': f'{id_1}:eventDetailDateTable',
            f'{id_1}:eventDetailDateTable': f'{id_1}:eventDetailDateTable',
            f'{id_1}:eventDetailDateTable_pagination': 'true',
            f'{id_1}:eventDetailDateTable_first': 0,
            f'{id_1}:eventDetailDateTable_rows': 20,
            f'{id_1}:eventDetailDateTable_skipChildren': 'true',
            f'{id_1}:eventDetailDateTable_encodeFeature': 'true',
            f'{id_1}_SUBMIT': '1',
        }
        stop = False
        while not stop:
            stop = True
            r = self.post(f'/course/educationDetails.xhtml', data, ajax=True)
            for cdata in CDATA.finditer(r.text):
                cd = cdata.group(1)
                if not cd.startswith('<tr'):
                    continue
                stop = False
                for row in TABLE_TR.finditer(cd):
                    event = [d.group(1) for d in TABLE_TD.finditer(row.group(1))]
                    if len(event) == 0:
                        continue

                    day, date, time_from_to, location = event[:4]
                    comment = event[-1]
                    append_events(date, time_from_to, location, comment)
            data[f'{id_1}:eventDetailDateTable_first'] += 20
        return events

    def get_course_extra_events(self, course: Course) -> List[Dict[str, Any]]:
        events = []

        # LVA-An/-Abmeldung
        uri = f'/education/course/courseRegistration.xhtml?semester={course.semester}&courseNr={course.nr}'
        r = self.get(uri)
        if r.status_code == 200:
            course_begin = LI_BEGIN.findall(r.text)
            course_end = LI_END.findall(r.text)
            course_deregend = LI_DEREGEND.findall(r.text)
            if len(course_begin) > 0:
                ts = datetime.datetime.strptime(course_begin[0], '%d.%m.%Y, %H:%M')
                events.append({
                    'id': f'{course.nr}-{course.semester}-LVA-anmeldung',
                    'start': ts,
                    'end': ts,
                    'name': 'Beginn LVA-Anmeldung',
                    'url': TISS_URL + uri,
                })
            if len(course_end) > 0 and len(course_deregend) > 0 and course_end[0] == course_deregend[0]:
                ts = datetime.datetime.strptime(course_end[0], '%d.%m.%Y, %H:%M')
                events.append({
                    'id': f'{course.nr}-{course.semester}-LVA-an-abmeldung-ende',
                    'start': ts,
                    'end': ts,
                    'name': 'Ende LVA-An/-Abmeldung',
                    'url': TISS_URL + uri,
                })
            else:
                if len(course_end) > 0:
                    ts = datetime.datetime.strptime(course_end[0], '%d.%m.%Y, %H:%M')
                    events.append({
                        'id': f'{course.nr}-{course.semester}-LVA-anmeldung-ende',
                        'start': ts,
                        'end': ts,
                        'name': 'Ende LVA-Anmeldung',
                        'url': TISS_URL + uri,
                    })
                if len(course_deregend) > 0:
                    ts = datetime.datetime.strptime(course_deregend[0], '%d.%m.%Y, %H:%M')
                    events.append({
                        'id': f'{course.nr}-{course.semester}-LVA-abmeldung-ende',
                        'start': ts,
                        'end': ts,
                        'name': 'Ende LVA-Abmeldung',
                        'url': TISS_URL + uri,
                    })

        # Gruppenan/-abmeldungen
        uri = f'/education/course/groupList.xhtml?semester={course.semester}&courseNr={course.nr}'
        r = self.get(uri)
        if r.status_code == 200:
            begins = set(LI_APP_BEGIN.findall(r.text))
            ends = set(LI_APP_END.findall(r.text))
            for b in begins:
                ts = datetime.datetime.strptime(b, '%d.%m.%Y, %H:%M')
                events.append({
                    'id': f'{course.nr}-{course.semester}-group-anmeldung-{b}',
                    'start': ts,
                    'end': ts,
                    'name': 'Beginn Gruppenanmeldung',
                    'url': TISS_URL + uri,
                })
            for e in ends:
                ts = datetime.datetime.strptime(e, '%d.%m.%Y, %H:%M')
                events.append({
                    'id': f'{course.nr}-{course.semester}-group-anmeldung-{e}',
                    'start': ts,
                    'end': ts,
                    'name': 'Ende Gruppenanmeldung',
                    'url': TISS_URL + uri,
                })

        # Prüfungen + An/-Abmeldungen
        uri = f'/education/course/examDateList.xhtml?semester={course.semester}&courseNr={course.nr}'
        r = self.get(uri)

        m = BUTTON_EXAM.search(r.text)
        if not m:
            raise tucal.TissError()

        id_1 = m.group(1)
        data = {
            'jakarta.faces.source': f'examDateListForm:{id_1}',
            'jakarta.faces.partial.execute': '@all',
            'jakarta.faces.partial.render': 'examDateListForm',
            f'examDateListForm:{id_1}': f'examDateListForm:{id_1}',
            'examDateListForm_SUBMIT': '1',
        }
        r = self.post(uri, data, ajax=True)
        if r.status_code == 200:
            exams = {}
            for exam_match in DIV_EXAM.finditer(r.text):
                name = exam_match.group(2).replace('.', '. ').replace('  ', ' ')
                date = datetime.datetime.strptime(exam_match.group(3), '%d.%m.%Y').date()
                status = exam_match.group(5)
                table = {
                    m.group(1).strip(): TAGS.sub('', m.group(2).strip())
                    for m in LABEL_EXAM.finditer(exam_match.group(6))
                }
                if table['Stoffsemester'] != str(course.semester) and status != 'angemeldet':
                    continue

                name_parsed = name.split('(')[0].strip().split(',')[0].strip()
                index = f'{date} {name_parsed}'.replace(' ', '-').lower()
                if index not in exams:
                    exams[index] = []
                table['meta'] = {
                    'status': status,
                    'date': date,
                    'name': name,
                    'name_parsed': name_parsed,
                }
                exams[index].append(table)

            for index, data in exams.items():
                begin, end, online_end = None, None, None
                begin_l, end_l, online_end_l = None, None, None
                name_parsed, date, stoffsemester = None, None, None
                enrolled = False
                for exam in data:
                    el = len(exam['meta']['name'])
                    name_parsed = exam['meta']['name_parsed']
                    date = exam['meta']['date']
                    stoffsemester = exam['Stoffsemester']

                    if exam['meta']['status'] == 'angemeldet':
                        enrolled = True

                    if 'Beginn der Anmeldung' in exam:
                        b = exam['Beginn der Anmeldung']
                        if begin is None or (begin != b and el < begin_l):
                            begin, begin_l = b, el

                    if 'Ende der Anmeldung' in exam:
                        e = exam['Ende der Anmeldung']
                        if end is None or (end != e and el < end_l):
                            end, end_l = e, el

                    if 'Ende der Online-Abmeldung' in exam:
                        e = exam['Ende der Online-Abmeldung']
                        if online_end is None or (online_end != e and el < online_end_l):
                            online_end, online_end_l = e, el

                begin = datetime.datetime.strptime(begin, '%d.%m.%Y, %H:%M') if begin else None
                end = datetime.datetime.strptime(end, '%d.%m.%Y, %H:%M') if end else None
                online_end = datetime.datetime.strptime(online_end, '%d.%m.%Y, %H:%M') if online_end else None

                if begin is None:
                    continue

                date_str = date.strftime('%d.%m.%Y')

                events.append({
                    'id': f'{course.nr}-exam-{date}-{name_parsed}',
                    'start': date,
                    'end': date + datetime.timedelta(days=1),
                    'name': name_parsed,
                    'url': TISS_URL + uri,
                    'exam': {
                        'stoffsemester': stoffsemester,
                        'reg_start': begin.isoformat(),
                        'reg_end': end.isoformat(),
                        'dereg_end': online_end.isoformat(),
                    }
                })
                events.append({
                    'id': f'{course.nr}-exam-{date}-{name_parsed}-anmeldung',
                    'start': begin,
                    'end': begin,
                    'name': f'Beginn Prüfungsanmeldung {name_parsed} ({date_str})',
                    'url': TISS_URL + uri,
                })

                if end == online_end:
                    events.append({
                        'id': f'{course.nr}-exam-{date}-{name_parsed}-an-abmeldung-ende',
                        'start': end,
                        'end': end,
                        'name': f'Ende Prüfungsan/-abmeldung {name_parsed} ({date_str})',
                        'url': TISS_URL + uri,
                    })
                else:
                    events.append({
                        'id': f'{course.nr}-exam-{date}-{name_parsed}-anmeldung-ende',
                        'start': end,
                        'end': end,
                        'name': f'Ende Prüfungsanmeldung {name_parsed} ({date_str})',
                        'url': TISS_URL + uri,
                    })
                    events.append({
                        'id': f'{course.nr}-exam-{date}-{name_parsed}-abmeldung-ende',
                        'start': online_end,
                        'end': online_end,
                        'name': f'Ende Prüfungsabmeldung {name_parsed} ({date_str})',
                        'url': TISS_URL + uri,
                    })

        return events
