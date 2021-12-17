
from typing import Optional, List, Tuple, Generator
import datetime
import html

import tucal


def _split(data: str, split: str = None) -> List[str]:
    parts = []
    cur = ''
    esc = False
    for ch in data:
        if esc:
            esc = False
            if ch == 'n':
                cur += '\n'
            elif ch == 't':
                cur += '\t'
            else:
                cur += ch
        elif ch == '\\':
            esc = True
        elif split is not None and ch in split:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    if len(cur) > 0:
        parts.append(cur)
    return parts


class Event:
    uid: Optional[str]
    sequence: Optional[int]
    summary: Optional[str]
    description: Optional[str]
    last_modified: Optional[datetime.datetime]
    access: Optional[datetime.datetime]
    start: Optional[datetime.datetime or datetime.date]
    end: Optional[datetime.datetime or datetime.date]
    categories: List[str]
    location: Optional[str]
    recurrence_id: Optional[str]
    url: Optional[str]
    conference: Optional[str]

    def __init__(self):
        self.uid = None
        self.sequence = None
        self.summary = None
        self.description = None
        self.last_modified = None
        self.access = None
        self.start = None
        self.end = None
        self.categories = []
        self.location = None
        self.recurrence_id = None
        self.url = None
        self.conference = None

    @property
    def uid_rec(self) -> str:
        if self.recurrence_id is not None:
            return f'{self.uid}-{self.recurrence_id}'
        else:
            return self.uid

    def _parse(self, dir_gen):
        for d, opt, val in dir_gen:
            if d == 'END':
                if val == 'VEVENT':
                    return
                else:
                    raise ValueError('invalid ical format')
            elif d == 'UID':
                self.uid = _split(val)[0] if len(val) > 0 else None
            elif d == 'SEQUENCE':
                self.sequence = int(_split(val)[0]) if len(val) > 0 else None
            elif d == 'RECURRENCE-ID':
                self.recurrence_id = _split(val)[0] if len(val) > 0 else None
            elif d == 'URL':
                self.url = _split(val)[0] if len(val) > 0 else None
            elif d == 'CONFERENCE':
                self.conference = _split(val)[0] if len(val) > 0 else None
            elif d == 'CATEGORIES':
                self.categories = [html.unescape(part).strip() for part in _split(val, ',')]
            elif d == 'SUMMARY':
                self.summary = html.unescape(_split(val)[0]).strip() if len(val) > 0 else None
            elif d == 'DESCRIPTION':
                self.description = html.unescape(_split(val)[0]).strip() if len(val) > 0 else None
            elif d == 'LOCATION':
                self.location = html.unescape(_split(val)[0]).strip() if len(val) > 0 else None
            elif d in ('DTSTART', 'DTEND', 'DTSTAMP', 'LAST-MODIFIED'):
                if len(opt) > 0 and opt[0] == 'VALUE=DATE':
                    iso = f'{val[:4]}-{val[4:6]}-{val[6:8]}'
                    dt = datetime.date.fromisoformat(iso)
                else:
                    iso = f'{val[:4]}-{val[4:6]}-{val[6:8]}T{val[9:11]}:{val[11:13]}:{val[13:15]}{val[15:]}'
                    dt = tucal.parse_iso_timestamp(iso, tz=opt[0].split('=')[1] if len(opt) > 0 else None)
                if d == 'DTSTART':
                    self.start = dt
                elif d == 'DTEND':
                    self.end = dt
                elif d == 'DTSTAMP':
                    self.access = dt
                elif d == 'LAST-MODIFIED':
                    self.last_modified = dt


class Timezone:
    def __init__(self):
        pass

    def _parse(self, dir_gen):
        for d, opt, val in dir_gen:
            if d == 'END' and val == 'VTIMEZONE':
                return


class Calendar:
    events: List[Event]

    def __init__(self):
        self.events = []

    def _parse(self, dir_gen):
        for d, opt, val in dir_gen:
            if d == 'END':
                if val == 'VCALENDAR':
                    return
                else:
                    raise ValueError('invalid ical format')
            elif d == 'BEGIN' and val == 'VEVENT':
                evt = Event()
                evt._parse(dir_gen)
                self.events.append(evt)
            elif d == 'BEGIN' and val == 'VTIMEZONE':
                Timezone()._parse(dir_gen)


def parse_ical(data: str) -> Calendar:
    def parse_line(line: str) -> Tuple[str, List[str], str]:
        directive, value = line.split(':', 1)
        directive = directive.split(';')
        directive, opts = directive[0], directive[1:]
        return directive, opts, value

    def gen() -> Generator[str, None, None]:
        last = None
        for cur in data.splitlines():
            if last is not None and len(cur) > 0 and cur[0] in ('\t', ' '):
                last += cur[1:]
                continue

            if last is not None:
                yield parse_line(last)
            if len(cur) > 0:
                last = cur
        if last is not None:
            yield parse_line(last)

    directives = gen()
    cal = None
    for d, opt, val in directives:
        if d == 'BEGIN' and val == 'VCALENDAR':
            cal = Calendar()
            cal._parse(directives)
        else:
            raise ValueError('invalid ical format')

    return cal
