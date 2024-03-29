# https://www.tuwien.at/tu-wien/aktuelles/veranstaltungskalender

from typing import List, Dict, Any
import json
import re
import datetime

import tucal.icalendar
import tucal
import tucal.db
import tuwien.sso


VEVENT = re.compile(r'(BEGIN:VEVENT(.*?)END:VEVENT)', re.MULTILINE | re.DOTALL)
DESCRIPTION = re.compile('(\r\nDESCRIPTION:)(.*?)(\r\n[A-Z]{6,}:)', re.MULTILINE | re.DOTALL)


ENDPOINT = 'https://www.tuwien.at/tu-wien/aktuelles/veranstaltungskalender'


def get_calendarize_url(endpoint: str, args: Dict[str, Any] = None) -> str:
    args = args or {}
    query = '&'.join([f'tx_calendarize_calendar%5B{key}%5D={value}' for key, value in args.items()])
    return f'{ENDPOINT}{endpoint}?{query}'


def repair_ics(data: str) -> str:
    repaired = 'BEGIN:VCALENDAR\r\n'
    for event in VEVENT.finditer(data):
        event = event.group(1)
        event = DESCRIPTION.sub(lambda m: m.group(1) + m.group(2).replace('\r\n', '\r\n ') + m.group(3), event)
        lines = event.split('\r\n')
        for i in range(len(lines)):
            line = lines[i]
            if not line.startswith('DT'):
                continue
            parts = line.split(':', 1)
            if 'T' in parts[1]:
                continue
            date = parts[1]
            if line.startswith('DTEND'):
                dt = datetime.date.fromisoformat(f'{date[:4]}-{date[4:6]}-{date[6:8]}') + datetime.timedelta(days=1)
                date = dt.strftime('%Y%m%d')
            lines[i] = parts[0].split(';')[0] + ';VALUE=DATE:' + date
        repaired += '\r\n'.join(lines + [''])
    repaired += 'END:VCALENDAR\r\n'
    return repaired


class Sync(tucal.Sync):
    events: List[tucal.icalendar.Event] = None

    def __init__(self, session: tuwien.sso.Session):
        super().__init__(session)
        self.events = []

    def fetch(self):
        session = self.session.session
        now = tucal.now()
        for year in range(now.year - 1, now.year + 2):
            r = session.get(get_calendarize_url('', {'year': year, 'format': 'ics'}))
            if r.status_code != 200:
                raise RuntimeError()

            # FIXME changed endpoint
            ical = tucal.icalendar.parse_ical(repair_ics(r.text))
            self.events += ical.events

    def store(self, cur: tucal.db.Cursor):
        if len(self.events) == 0:
            return

        group_nr = tucal.get_group_nr(cur, 'TU Events', True)

        rows = [{
            'source': 'tuwien-events',
            'id': event.uid,
            'group': group_nr,
            'start': event.start,
            'end': event.end,
            'data': json.dumps({'tuwien': {
                'summary': event.summary,
                'description': event.description,
                'location': event.location,
                'url': f'{ENDPOINT}/cal-event/idx-{event.uid.split("-")[-1]}',
                'day_event': not isinstance(event.start, datetime.datetime),
            }}),
        } for event in self.events]

        fields = {
            'source': 'source',
            'event_id': 'id',
            'start_ts': 'start',
            'end_ts': 'end',
            'group_nr': 'group',
            'data': 'data',
        }
        tucal.db.upsert_values('tucal.external_event', rows, fields, ('source', 'event_id'), {'data': 'jsonb'})
        ids_now = {row['id'] for row in rows}

        start_min = min([datetime.datetime.fromordinal(e['start'].toordinal()) for e in rows])

        cur.execute("LOCK TABLE tucal.external_event IN SHARE ROW EXCLUSIVE MODE")
        cur.execute("""
            SELECT event_id
            FROM tucal.external_event
            WHERE source = 'tuwien-events' AND NOT deleted AND
                  start_ts >= %s""", (start_min,))
        ids_db = {row[0] for row in cur.fetch_all()}

        ids_del = ids_db - ids_now
        cur.execute("""
            UPDATE tucal.external_event
            SET deleted = true
            WHERE source = 'tuwien-events' AND event_id = ANY(%s)""", (list(ids_del),))


class Plugin(tucal.Plugin):
    @staticmethod
    def sync() -> Sync:
        return Sync(tuwien.sso.Session())

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session) -> None:
        return None
