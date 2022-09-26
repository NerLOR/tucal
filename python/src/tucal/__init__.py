
from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple, Generator
from configparser import ConfigParser
import datetime
import pytz
import sys
import time
import json
import socket

import tuwien.sso


CONFIG_PLACES = ['tucal.ini', '/etc/tucal/tucal.ini', '../../tucal.ini']


def get_config() -> ConfigParser:
    for file_name in CONFIG_PLACES:
        try:
            with open(file_name) as f:
                parser = ConfigParser()
                parser.read_file(f)
                return parser
        except FileNotFoundError or PermissionError:
            pass
    raise FileNotFoundError('config file not found')


class LoginError(Exception):
    pass


class InvalidCredentialsError(LoginError):
    pass


class JobFormatError(Exception):
    pass


class CourseNotFoundError(Exception):
    pass


class RoomNotFoundError(Exception):
    pass


class TissError(Exception):
    pass


class Plugin:
    @staticmethod
    def sync() -> Optional[Sync]:
        raise NotImplementedError()

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session) -> Optional[Sync]:
        raise NotImplementedError()


class Sync:
    session: tuwien.sso.Session

    def __init__(self, session: tuwien.sso.Session):
        self.session = session

    def fetch(self):
        raise NotImplementedError()

    def store(self, cursor):
        raise NotImplementedError()

    def sync(self, cursor):
        self.fetch()
        self.store(cursor)


def parse_iso_timestamp(iso: str, default: bool = False, tz: str = None) -> datetime.datetime:
    if iso[-1] == 'Z':
        iso = iso[:-1] + '+00:00'
    elif iso[-5] == '+':
        iso = iso[:-2] + ':' + iso[-2:]
    dt = datetime.datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        if tz is not None:
            dt = pytz.timezone(tz).localize(dt)
        elif default:
            dt = pytz.timezone('Europe/Vienna').localize(dt)
        else:
            dt = dt.astimezone()
    return dt


def date_to_datetime(date: datetime.date, default: bool = False, tz: str = None) -> datetime.datetime:
    dt = datetime.datetime.combine(date, datetime.datetime.min.time())
    if tz is not None:
        dt = pytz.timezone(tz).localize(dt)
    elif default:
        dt = pytz.timezone('Europe/Vienna').localize(dt)
    else:
        dt = dt.astimezone()
    return dt


def now() -> datetime.datetime:
    return datetime.datetime.now().astimezone()


# FIXME not up to date socket interface
# FIXME used anywhere?
def schedule_job(name: str, *args):
    reader = JobStatus()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect('/var/tucal/scheduler.sock')
        client.send(' '.join([name, *args]).encode('utf8') + b'\n')
        msg = client.recv(64).strip().decode('utf8')
        if msg.startswith('error:'):
            raise RuntimeError(msg[6:].strip())

        job_nr, job_id, pid = msg.split(' ')

        fin = False
        while not fin:
            line = client.recv(1024)
            if line.startswith(b'stdout:'):
                line = line[7:].decode('utf8')
                if not reader.line(line):
                    time.sleep(0.125)
                    continue
            elif line.startswith(b'status:') or len(line) == 0:
                fin = True
            yield reader, fin


def get_group_nr(cursor, group_name: str, public_group: bool = False):
    cursor.execute("SELECT group_nr FROM tucal.group WHERE group_name = %s", (group_name,))
    rows = cursor.fetch_all()
    if len(rows) > 0:
        return rows[0][0]

    cursor.execute("INSERT INTO tucal.group (group_name, public) VALUES (%s, %s) RETURNING group_nr",
                   (group_name, public_group))
    rows = cursor.fetch_all()
    return rows[0][0]


def get_course_group_nr(cursor, course_nr: str, semester: Semester):
    cursor.execute("SELECT group_nr FROM tucal.group_link WHERE (course_nr, semester, name) = (%s, %s, 'LVA')",
                   (str(course_nr), str(semester)))
    rows = cursor.fetch_all()
    if len(rows) > 0:
        return rows[0][0]

    cursor.execute("INSERT INTO tucal.group (group_name) VALUES (%s) RETURNING group_nr",
                   (f'{course_nr}-{semester} LVA',))
    rows = cursor.fetch_all()
    group_nr = rows[0][0]
    cursor.execute("INSERT INTO tucal.group_link (group_nr, course_nr, semester, name) VALUES (%s, %s, %s, 'LVA')",
                   (group_nr, str(course_nr), str(semester)))
    return group_nr


class Semester:
    _year: int
    _sem: str

    def __init__(self, semester: str):
        if semester[1] == 'S':
            self._year = int(semester[2:])
            if self._year < 100:
                self._year += 2000
            self._sem = semester[0].upper()
        else:
            self._year = int(semester[:4])
            self._sem = semester[-1].upper()
        if self._sem not in 'WS':
            raise ValueError(f"invalid semester '{semester}'")

    def __int__(self) -> int:
        return self._year * 2 + (1 if self._sem == 'W' else 0)

    def __str__(self) -> str:
        return f'{self._year}{self._sem}'

    def __repr__(self) -> str:
        return f'{self._year}{self._sem}'

    def __eq__(self, other: Semester) -> bool:
        return isinstance(other, Semester) and self._year == other._year and self._sem == other._sem

    def __gt__(self, other: Semester) -> bool:
        return int(self) > int(other)

    def __lt__(self, other: Semester) -> bool:
        return int(self) < int(other)

    def __next__(self) -> Semester:
        return self + 1

    def __add__(self, other: int) -> Semester:
        if isinstance(other, int):
            c = int(self) + other
            return Semester(f'{c // 2}{"W" if c % 2 == 1 else "S"}')
        else:
            raise ValueError(f'unable to add type {type(other)} to Semester')

    def __sub__(self, other: int or Semester) -> int or Semester:
        if isinstance(other, Semester):
            return int(self) - int(other)
        elif isinstance(other, int):
            return self.__add__(-other)
        else:
            raise ValueError(f'unable to subtract type {type(other)} from Semester')

    def __hash__(self) -> int:
        return int(self)

    @property
    def year(self) -> int:
        return self._year

    @property
    def sem(self) -> str:
        return self._sem

    @property
    def first_day(self) -> datetime.datetime:
        if self._sem == 'W':
            return datetime.datetime(year=self._year, month=10, day=1)
        else:
            return datetime.datetime(year=self._year, month=3, day=1)

    @property
    def last_day(self) -> datetime.datetime:
        return (self + 1).first_day - datetime.timedelta(seconds=1)

    @staticmethod
    def from_date(date: datetime.datetime) -> Semester:
        if date.month >= 10:
            return Semester(f'{date.year}W')
        elif date.month <= 2:
            return Semester(f'{date.year - 1}W')
        else:
            return Semester(f'{date.year}S')

    @staticmethod
    def from_date_strict(date: datetime.datetime) -> Optional[Semester]:
        if date.month >= 10:
            return Semester(f'{date.year}W')
        elif date.month <= 1:
            return Semester(f'{date.year - 1}W')
        elif 3 <= date.month <= 6:
            return Semester(f'{date.year}S')
        else:
            return None

    @staticmethod
    def from_int(num: int) -> Semester:
        return Semester(f'{num // 2}{"W" if num % 2 == 1 else "S"}')

    @staticmethod
    def current() -> Semester:
        return Semester.from_date(now())

    @staticmethod
    def last() -> Semester:
        return Semester.current() - 1

    @staticmethod
    def next() -> Semester:
        return Semester.current() + 1


class Job:
    perc_steps: List[int]
    initialized: bool
    _perc: int
    _name: str
    _proc_start: float
    _clock_id: int
    _step_mult: List[float]
    _indent: int
    _pop_indents: List[int]

    def __init__(self, name: str = None, sub_steps: int = None, perc_steps: int = None, estimate: int = None):
        self.initialized = False
        self._indent = 0
        self._pop_indents = [-1]
        if name or sub_steps or perc_steps or estimate:
            self.init(name, sub_steps, perc_steps, estimate)

    def init(self, name: str, sub_steps: int, perc_steps: int = 1, estimate: int = None):
        if self.initialized:
            self.perc_steps.append(perc_steps)
            self._pop_indents.append(self._indent)
            self.begin(name, sub_steps)
            return

        self.initialized = True
        self.perc_steps = [perc_steps]
        self._perc = 0
        self._name = name
        self._clock_id = time.CLOCK_MONOTONIC
        self._step_mult = [1]
        self._proc_start = time.clock_gettime(self._clock_id)
        print(f'**start={now().isoformat()}')
        if estimate:
            print(f'**estimate={estimate}')
        print(f'*{self._format_time()}:0.0000::START:{sub_steps}:{name}')
        sys.stdout.flush()

    def begin(self, name: str, sub_steps: int = 0):
        self._indent += 1
        print(f'*{self._format_time()}:{self._perc:.4f}:{"-" * self._indent}:START:{sub_steps}:{name}')
        sys.stdout.flush()

    def step(self, steps: int):
        self._perc += steps / self.perc_steps[-1] * self._step_mult[-1] if self.perc_steps[-1] != 0 else 0
        if self._indent == 0 and self._perc < 1:
            self._perc = 1

    def end(self, steps: int):
        self._perc += steps / self.perc_steps[-1] * self._step_mult[-1] if self.perc_steps[-1] != 0 else 0
        if self._indent == 0 and self._perc < 1:
            self._perc = 1
        print(f'*{self._format_time()}:{self._perc:.4f}:{"-" * self._indent}:STOP')
        self._indent -= 1
        if self._indent == self._pop_indents[-1]:
            self._pop_indents.pop()
            self.perc_steps.pop()
        sys.stdout.flush()

    def sub_stop(self, steps: int):
        self._perc += steps / self.perc_steps[-1] * self._step_mult[-1]

    def exec(self, steps: int, func, job: bool = True, **kwargs):
        self._step_mult.append(self._step_mult[-1] * steps / self.perc_steps[-1])
        if job:
            kwargs['job'] = self
        func(**kwargs)
        self._step_mult.pop()

    def _format_time(self) -> str:
        return f'{time.clock_gettime(self._clock_id) - self._proc_start:8.4f}'


class JobStatus:
    progress: float
    start: Optional[datetime.datetime]
    time: float
    steps: List[Dict[str, Any]]
    comments: List[str]
    finished: bool
    success: bool
    current_step: Optional[Tuple]
    estimate: Optional[int]

    def __init__(self):
        self.progress = 0
        self.start = None
        self.time = 0
        self.steps = []
        self.comments = []
        self.finished = False
        self.success = False
        self.current_step = None
        self.estimate = None

    def line(self, line: str) -> bool:
        if len(line) == 0:
            return False
        line = line.rstrip()
        if len(line) == 0:
            return True
        elif line[0] != '*':
            cur = self.get_current_step()
            if cur is not None:
                cur['comments'].append(line)
            else:
                self.comments.append(line)
            return True
        line = line[1:].strip()

        if line.startswith('*'):
            meta = [p.strip() for p in line[1:].strip().split('=', 1)]
            if len(meta) != 2:
                raise JobFormatError('invalid job format')

            if meta[0] == 'start':
                self.start = parse_iso_timestamp(meta[1])
            elif meta[0] == 'estimate':
                self.estimate = int(meta[1])
            else:
                raise JobFormatError('invalid job format')
            return True

        line = line.split(':', 4)
        if len(line) < 4:
            raise JobFormatError('invalid job format')

        time_sec = float(line[0])
        self.time = time_sec
        self.progress = float(line[1])

        line.pop(2)
        cmd = line[2]
        if cmd == 'STOP':
            if len(line) > 3 or self.current_step is None:
                raise JobFormatError('invalid job format')
            if len(self.current_step) == 1:
                self.current_step = None
                self.finished = True
                self.success = True
            else:
                step = self.get_current_step()
                step['end'] = time_sec
                step['time'] = step['end'] - step['start']

                self.current_step = self.current_step[:-1]
                step = self.get_current_step()
                step['next_step_nr'] += 1
        elif cmd == 'START':
            step_num, name = line[3].split(':', 1)
            step_num = int(step_num)

            step = self.get_current_step()

            if step_num == 0:
                if self.current_step is None:
                    self.current_step = (0, step['next_step_nr'])
                else:
                    self.current_step = self.current_step + (step['next_step_nr'],)

                if self.current_step[-1] >= len(step['steps']):
                    raise JobFormatError('invalid job format')

                step = self.get_current_step()
                step['name'] = name
                step['start'] = time_sec
                step['end'] = None
                step['time'] = None
                step['steps'] = None
                step['comments'] = []
            else:
                if step is None:
                    self.steps.append({})
                    step = self.steps[0]
                    self.current_step = (0,)
                else:
                    self.current_step = self.current_step + (step['next_step_nr'],)
                    if self.current_step[-1] >= len(step['steps']):
                        raise JobFormatError('invalid job format')
                    step = self.get_current_step()

                step['name'] = name
                step['next_step_nr'] = 0
                step['start'] = time_sec
                step['end'] = None
                step['time'] = None
                step['steps'] = []
                step['comments'] = []
                for i in range(step_num):
                    step['steps'].append({})
        else:
            raise JobFormatError('invalid job format')
        return True

    def get_current_step(self) -> Optional[Dict[str, Any]]:
        if len(self.steps) == 0:
            return None
        cur = self.steps[0]
        if self.current_step is None:
            return cur
        for idx in self.current_step[1:]:
            cur = cur['steps'][idx]
        return cur

    def path(self) -> Generator[Tuple[Dict[str, Any], int]]:
        cur = self.steps[0]
        yield cur, 1, 1
        if self.current_step is None:
            return
        for idx in self.current_step[1:]:
            step_num = len(cur['steps'])
            cur = cur['steps'][idx]
            yield cur, idx + 1, step_num
        return

    def _json(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cur = self.get_current_step()
        updated = []
        for step in steps:
            if 'name' not in step:
                updated.append({})
                continue
            running = (step['steps'] is None and step == cur) or \
                      (step['steps'] is not None and len(step['steps']) != step['next_step_nr'])
            updated.append({
                'name': step['name'],
                'time': step['time'] or self.time - step['start'],
                'is_running': running,
                'comments': step['comments'],
            })
            if step['steps'] is None:
                updated[-1]['steps'] = None
            else:
                updated[-1]['steps'] = self._json(step['steps'])
        return updated

    def json(self) -> str:
        eta = self.time / self.progress if self.progress > 0 else self.estimate
        data = {
            'progress': self.progress,
            'is_running': not self.finished,
            'start_ts': self.start.isoformat() if self.start else None,
            'time': self.time,
            'remaining': eta - self.time if eta else None,
            'eta_ts': (self.start + datetime.timedelta(seconds=eta)).isoformat() if eta else None,
            'name': self.steps[0]['name'] if len(self.steps) > 0 else None,
            'steps': self._json(self.steps[0]['steps']) if len(self.steps) > 0 else None,
            'comments': self.comments,
        }
        return json.dumps(data)
