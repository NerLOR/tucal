# https://events.htu.at/

import requests
import json

import tucal
import tucal.db

QUERY = {
  "operationName": "FetchEvents",
  "variables": {
    "page": 1,
    "limit": 50
  },
  "query": """query FetchEvents($orderBy: EventOrderBy, $direction: SortDirection, $page: Int, $limit: Int)
  { events(orderBy: $orderBy, direction: $direction, page: $page, limit: $limit)
  { total elements { id url title description beginsOn endsOn status picture { id url }
  physicalAddress { id description locality } tags { ...TagFragment } } }}
  fragment TagFragment on Tag { id title}"""
}

EVENTS_HTU_HOST = 'events.htu.at'
EVENTS_HTU = f'https://{EVENTS_HTU_HOST}'


class Plugin(tucal.Plugin):
    @staticmethod
    def sync():
        r = requests.post(f'{EVENTS_HTU}/api', json=QUERY)
        if r.status_code != 200:
            raise RuntimeError()

        raw_events = r.json()
        events = raw_events['data']['events']['elements']

        rows = []
        for event in events:
            rows.append({
                'source': 'htu-events',
                'id': event['id'],
                'start': tucal.parse_iso_timestamp(event['beginsOn'], True),
                'end': tucal.parse_iso_timestamp(event['endsOn'], True),
                'data': json.dumps({'htu': event}),
            })

        fields = {
            'source': 'source',
            'event_id': 'id',
            'start_ts': 'start',
            'end_ts': 'end',
            # 'group_nr': 'group',
            'data': 'data',
        }
        tucal.db.upsert_values('tucal.external_event', rows, fields, ('source', 'event_id'), {'data': 'jsonb'})
        tucal.db.commit()
