# 187.B12 VU Denkweisen der Informatik

from typing import Dict
import requests
import requests.cookies
import json
import re
import html
import datetime

import tucal
import tucal.db
import tucal.icalendar
import tuwien.sso

RE_TOKEN = re.compile(r'"token": ("([^"]*)"|null), "pk": (([0-9]+)|null),')
RE_DATES = re.compile(r'<div class="header collapse[^>]*>([^\n]*)|\s*([^<>]*)\s*<i[^>]* data-block="([^"]*)">',
                      re.DOTALL | re.MULTILINE)
RE_THINKING = re.compile(r'([A-Z][a-z]+) Thinking')

WEBCAL = 'https://p101-caldav.icloud.com/published/2/' \
         'MzgyNDc0ODczODI0NzQ4N6wcQX1kdbFRkK0NDrPux_KFL1TO6WWudBvZC5LkC8jII-EKirQ5vlMF0ygrdaHcTzQMX_rXGyWk6aEK3ptjEaU'

AURORA_HOST = 'aurora.iguw.tuwien.ac.at'
REVIEW_HOST = 'review.iguw.tuwien.ac.at'

AURORA = f'https://{AURORA_HOST}'
LITTLE_AURORA = f'https://{REVIEW_HOST}'


class Sync(tucal.Sync):
    cal: tucal.icalendar.Calendar = None

    def __init__(self, session: tuwien.sso.Session):
        super().__init__(session)

    def fetch(self):
        session = self.session.session
        r = session.get(WEBCAL)
        if r.status_code != 200:
            raise RuntimeError()

        self.cal = tucal.icalendar.parse_ical(r.text)

    def store(self, cur: tucal.db.Cursor):
        group_nr = tucal.get_course_group_nr(cur, '187B12', tucal.Semester('2021W'))

        rows = []
        for evt in self.cal.events:
            if evt.summary.startswith('Abgabe:') or evt.summary.startswith('Ende Reviewing:') or \
                    evt.summary.startswith('Finale Abgabe:') or evt.summary.startswith('Start:'):
                continue
            rows.append({
                'source': '187B12-aurora',
                'id': evt.uid_rec,
                'start': evt.start,
                'end': evt.end,
                'group': group_nr,
                'del': evt.summary.startswith('kein dwi') or 'Pause' in evt.summary,
                'data': json.dumps({
                    'aurora': {
                        'summary': evt.summary,
                        'conference': evt.url,
                        'type': 'lecture' if evt.summary.lower().startswith('intro') else 'course',
                    },
                }),
            })

        fields = {
            'source': 'source',
            'event_id': 'id',
            'start_ts': 'start',
            'end_ts': 'end',
            'group_nr': 'group',
            'deleted': 'del',
            'data': 'data'
        }
        tucal.db.upsert_values('tucal.external_event', rows, fields, ('source', 'event_id'), {'data': 'jsonb'})
        ids_now = {row['id'] for row in rows}

        cur.execute("LOCK TABLE tucal.external_event IN SHARE ROW EXCLUSIVE MODE")
        cur.execute("SELECT event_id FROM tucal.external_event WHERE source = '187B12-aurora' AND NOT deleted")
        ids_db = {row[0] for row in cur.fetch_all()}

        ids_del = ids_db - ids_now
        cur.execute("""
            UPDATE tucal.external_event
            SET deleted = true
            WHERE source = '187B12-aurora' AND event_id = ANY(%s)""", (list(ids_del),))


class SyncAuth(tucal.Sync):
    events: Dict[str, Dict] = None

    def __init__(self, session: tuwien.sso.Session):
        super().__init__(session)

    def fetch(self):
        session = self.session.session
        session.get(AURORA)
        session.get(f'{AURORA}/course/dwi/login/?next=/course/dwi/')
        r = session.get('https://login.tuwien.ac.at/AuthServ/AuthServ.authenticate?app=131&param=/course/dwi/')
        if r.status_code != 200:
            raise RuntimeError()

        r = session.get(f'{AURORA}/dcall_login/dcall_login.js')
        if r.status_code != 200:
            raise RuntimeError()

        m = RE_TOKEN.search(r.text)
        if not m:
            raise RuntimeError()

        cookies = session.cookies
        session_id = cookies.get('sessionid', domain=AURORA_HOST)
        c = requests.cookies.create_cookie('sessionid', session_id, domain=REVIEW_HOST)
        cookies.set_cookie(c)

        token, pk = m.group(2), m.group(4)
        session.post(f'{LITTLE_AURORA}/aurora_login/login/', {
            'token': token,
            'pk': pk,
        })

        r = session.get(f'{LITTLE_AURORA}/course/overview')
        if r.status_code != 200:
            raise RuntimeError()

        assignments = {}
        current_assignment = None
        for m in RE_DATES.finditer(r.text):
            new_assignment = m.group(1)
            if new_assignment:
                current_assignment = html.unescape(new_assignment).strip()
                assignments[current_assignment] = {}
            else:
                state = m.group(2).strip().lower()
                deadline = m.group(3).strip()

                if state.startswith('revisions/reflection'):
                    s = 'reflection'
                elif state.startswith('reviewing'):
                    s = 'reviewing'
                elif 'reviewing' in assignments[current_assignment] and state in ('ends', 'end', 'ended'):
                    s = 'reviewing_end'
                elif state in ('starts', 'start', 'started'):
                    s = 'start'
                else:
                    s = 'end'
                dt = datetime.datetime.strptime(deadline, '%d.%m, %H:%M')
                if dt.month >= 6:
                    dt = dt.replace(year=2021)
                else:
                    dt = dt.replace(year=2022)
                assignments[current_assignment][s] = dt

        self.events = {}
        for ass, data in assignments.items():
            idx = ass
            if ass.startswith('Zusammenfassung'):
                idx = ass
            elif 'Thinking' in ass:
                m = RE_THINKING.findall(ass)
                idx = f'Challenge {m[0]} Thinking'
            if idx not in self.events:
                self.events[idx] = {}
                if 'Challenge' in idx:
                    self.events[idx]['challenges'] = []
            evt = self.events[idx]
            if 'Challenge' in idx:
                evt['challenges'].append(ass)
            evt.update(data)

    def store(self, cur: tucal.db.Cursor):
        # TODO (LITTLE) AURORA HAS TO BE EXTERMINATED
        group_nr = tucal.get_course_group_nr(cur, '187B12', tucal.Semester('2021W'))

        rows = []
        for name, event in self.events.items():
            for sub in ('end', 'reviewing_end', 'reflection'):
                if sub not in event:
                    break
                evt_id = name.replace(' ', '-')\
                             .replace('Zusammenfassung', 'zsfg')\
                             .replace('Challenge', 'chlge')\
                             .lower() + '-' + sub.replace('_', '-')

                suffix = 'Reviewing' if sub == 'reviewing_end' else 'Reflection' if sub == 'reflection' else None
                data = {
                    'aurora': {
                        'summary': name + ((' - ' + suffix) if suffix else ''),
                        'url': f'{LITTLE_AURORA}/course/overview',
                    }
                }
                if 'challenges' in event:
                    data['aurora']['challenges'] = event['challenges']
                rows.append({
                    'source': '187B12-review',
                    'id': evt_id,
                    'ts': event[sub],
                    'group': group_nr,
                    'data': json.dumps(data),
                })

        fields = {
            'source': 'source',
            'event_id': 'id',
            'start_ts': 'ts',
            'end_ts': 'ts',
            'group_nr': 'group',
            'data': 'data',
        }
        tucal.db.upsert_values('tucal.external_event', rows, fields, ('source', 'event_id'), {'data': 'jsonb'})


class Plugin(tucal.Plugin):
    @staticmethod
    def sync() -> Sync:
        return Sync(tuwien.sso.Session())

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session):
        return SyncAuth(sso)
