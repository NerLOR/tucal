
from __future__ import annotations
import datetime
import typing
import sys
import time
import json
import socket

import tuwien.sso


class LoginError(Exception):
    pass


class InvalidCredentialsError(LoginError):
    pass


class JobFormatError(Exception):
    pass


class Plugin:
    @staticmethod
    def sync():
        pass

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session):
        pass


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


class Semester:
    _year: int
    _sem: str

    def __init__(self, semester: str):
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
        return (self + 1).next().first_day - datetime.timedelta(seconds=1)

    @staticmethod
    def from_date(date: datetime.datetime) -> Semester:
        if date.month >= 10:
            return Semester(f'{date.year}W')
        elif date.month <= 2:
            return Semester(f'{date.year - 1}W')
        else:
            return Semester(f'{date.year}S')

    @staticmethod
    def from_date_strict(date: datetime.datetime) -> typing.Optional[Semester]:
        if date.month >= 10:
            return Semester(f'{date.year}W')
        elif date.month <= 1:
            return Semester(f'{date.year - 1}W')
        elif 3 <= date.month <= 6:
            return Semester(f'{date.year}S')
        else:
            return None

    @staticmethod
    def current() -> Semester:
        return Semester.from_date(datetime.datetime.utcnow())

    @staticmethod
    def last() -> Semester:
        return Semester.current() - 1

    @staticmethod
    def next() -> Semester:
        return Semester.current() + 1


class Job:
    perc_steps: int
    _n: int
    _name: str
    _proc_start: float
    _clock_id: int

    def __init__(self, name: str, sub_steps: int, perc_steps: int = 1, estimate: int = None):
        self.perc_steps = perc_steps
        self._n = 0
        self._name = name
        self._clock_id = time.CLOCK_MONOTONIC
        self._proc_start = time.clock_gettime(self._clock_id)
        print(f'**{datetime.datetime.now().astimezone().isoformat()}')
        if estimate:
            print(f'**{estimate}')
        print(f'*{self._format_time()}:0.0000:START:{sub_steps}:{name}')
        sys.stdout.flush()

    def begin(self, name: str, sub_steps: int = 0):
        print(f'*{self._format_time()}:{self._n / self.perc_steps:.4f}:START:{sub_steps}:{name}')
        sys.stdout.flush()

    def end(self, steps: int):
        self._n += steps
        print(f'*{self._format_time()}:{self._n / self.perc_steps:.4f}:STOP')
        sys.stdout.flush()

    def sub_stop(self, steps: int):
        self._n += steps

    def _format_time(self) -> str:
        return f'{time.clock_gettime(self._clock_id) - self._proc_start:7.4f}'


class JobStatus:
    progress: float
    start: typing.Optional[datetime.datetime]
    time: float
    steps: typing.List[typing.Dict[str, typing.Any]]
    comments: typing.List[str]
    finished: bool
    success: bool
    current_step: typing.Optional[typing.Tuple]
    estimate: typing.Optional[int]

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
            if self.start is None:
                self.start = datetime.datetime.fromisoformat(line[1:]).astimezone()
            elif self.estimate is None:
                self.estimate = int(line[1:])
            else:
                raise JobFormatError('invalid job format')
            return True

        line = line.split(':', 3)
        if len(line) < 3:
            raise JobFormatError('invalid job format')

        time_sec = float(line[0])
        self.time = time_sec
        self.progress = float(line[1])

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

    def get_current_step(self) -> typing.Optional[typing.Dict[str, typing.Any]]:
        if len(self.steps) == 0:
            return None
        cur = self.steps[0]
        if self.current_step is None:
            return cur
        for idx in self.current_step[1:]:
            cur = cur['steps'][idx]
        return cur

    def path(self) -> typing.Generator[typing.Tuple[typing.Dict[str, typing.Any], int]]:
        cur = self.steps[0]
        yield cur, 1, 1
        if self.current_step is None:
            return
        for idx in self.current_step[1:]:
            step_num = len(cur['steps'])
            cur = cur['steps'][idx]
            yield cur, idx + 1, step_num
        return

    def _json(self, steps: typing.List[typing.Dict[str, typing.Any]]) -> typing.List[typing.Dict[str, typing.Any]]:
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
