
import typing
import datetime
import pytz
import html


def _split(data: str, split: str = None) -> typing.List[str]:
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
    uid: typing.Optional[str]
    summary: typing.Optional[str]
    description: typing.Optional[str]
    last_modified: typing.Optional[datetime.datetime]
    access: typing.Optional[datetime.datetime]
    start: typing.Optional[datetime.datetime or datetime.date]
    end: typing.Optional[datetime.datetime or datetime.date]
    categories: typing.List[str]
    location: typing.Optional[str]

    def __init__(self):
        self.uid = None
        self.summary = None
        self.description = None
        self.last_modified = None
        self.access = None
        self.start = None
        self.end = None
        self.categories = []
        self.location = None

    def _parse(self, dir_gen):
        for d, opt, val in dir_gen:
            if d == 'END':
                if val == 'VEVENT':
                    return
                else:
                    raise ValueError('invalid ical format')
            elif d == 'UID':
                self.uid = _split(val)[0] if len(val) > 0 else None
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
                    dat = datetime.date.fromisoformat(iso)
                else:
                    iso = f'{val[:4]}-{val[4:6]}-{val[6:8]}T{val[9:11]}:{val[11:13]}:{val[13:15]}'
                    if val[-1] == 'Z':
                        dat = datetime.datetime.fromisoformat(iso).astimezone(pytz.UTC)
                    elif len(opt) > 0:
                        tz = pytz.timezone(opt[0].split('=')[1])
                        dat = datetime.datetime.fromisoformat(iso).astimezone(tz)
                if d == 'DTSTART':
                    self.start = dat
                elif d == 'DTEND':
                    self.end = dat
                elif d == 'DTSTAMP':
                    self.access = dat
                elif d == 'LAST-MODIFIED':
                    self.last_modified = dat


class Timezone:
    def __init__(self):
        pass

    def _parse(self, dir_gen):
        for d, opt, val in dir_gen:
            if d == 'END' and val == 'VTIMEZONE':
                return


class Calendar:
    events: typing.List[Event]

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
    def parse_line(line: str) -> typing.Tuple[str, typing.List[str], str]:
        directive, value = line.split(':', 1)
        directive = directive.split(';')
        directive, opts = directive[0], directive[1:]
        return directive, opts, value

    def gen() -> typing.Generator[str, None, None]:
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
