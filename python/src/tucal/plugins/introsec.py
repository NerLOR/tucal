# 184.783 VU Introduction to Security
# 192.082 UE Introduction to Security

from typing import Dict
import json
import datetime

import tucal
import tucal.db
import tuwien.sso


CTFORGE = 'https://is.hackthe.space'


class Sync(tucal.Sync):
    lva: str = None
    lva_nr: str = None
    events: Dict[str, Dict] = None

    def __init__(self, lva: str, session: tuwien.sso.Session):
        if lva == 'VU':
            self.lva_nr = '184783'
        elif lva == 'UE':
            self.lva_nr = '192082'
        else:
            raise ValueError('argument lva may only be VU or UE')
        self.lva = lva
        super().__init__(session)

    def fetch(self):
        session = self.session.session
        r = session.get(f'{CTFORGE}/challenges/list', headers={
            'Referer': f'https://{CTFORGE}/',
        })
        if r.status_code != 200:
            raise RuntimeError()

        challenges = json.loads(r.text)
        self.events = {}
        for c in challenges:
            tags = [t.strip() for t in c['tags'].split(',')]
            if self.lva not in tags:
                continue
            c_id = c['submission_ending_time']
            self.events[f'{c_id}-start'] = {
                'name': c['name'],
                'type': 'start',
                'ts': datetime.datetime.fromisoformat(c['submission_starting_time']),
                'tags': tags,
            }
            self.events[f'{c_id}-end'] = {
                'name': c['name'],
                'type': 'end',
                'ts': datetime.datetime.fromisoformat(c['submission_ending_time']),
                'tags': tags,
            }

    def store(self, cur: tucal.db.Cursor):
        group_nr = tucal.get_course_group_nr(cur, self.lva_nr, tucal.Semester('2023S'))

        rows = []
        for e_id, event in self.events.items():
            rows.append({
                'source': f'{self.lva_nr}-ctforge',
                'id': e_id,
                'ts': event['ts'],
                'group': group_nr,
                'data': json.dumps({
                    'ctforge': {
                        'challenge': event['name'],
                        'type': event['type'],
                        'tags': event['tags'],
                        'url': f'{CTFORGE}/#/challenges/{event["name"]}'
                    }
                }),
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


class SyncAuth(tucal.Sync):
    lva: str = None
    events: Dict[str, Dict] = None

    def __init__(self, lva: str, session: tuwien.sso.Session):
        if lva not in ('VU', 'UE'):
            raise ValueError('argument lva may only be VU or UE')
        self.lva = lva
        super().__init__(session)

    def fetch(self):
        pass

    def store(self, cursor):
        pass


class PluginVU(tucal.Plugin):
    @staticmethod
    def sync() -> Sync:
        return Sync('VU', tuwien.sso.Session())

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session):
        return SyncAuth('VU', sso)


class PluginUE(tucal.Plugin):
    @staticmethod
    def sync() -> Sync:
        return Sync('UE', tuwien.sso.Session())

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session):
        return SyncAuth('UE', sso)
