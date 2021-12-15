import requests
import json

import tucal
import tucal.db
import tuwien.sso

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


class HTUEvents(tucal.Plugin):
    @staticmethod
    def sync():
        r = requests.post(f'{EVENTS_HTU}/api', json=QUERY)
        if r.status_code != 200:
            raise RuntimeError()

        cur = tucal.db.cursor()

        raw_events = r.json()
        events = raw_events['data']['events']['elements']

        for event in events:
            data = {
                'id': event['id'],
                'start': tucal.parse_iso_timestamp(event['beginsOn'], True),
                'end': tucal.parse_iso_timestamp(event['endsOn'], True),
                'data': json.dumps({'htu': event})
            }

            cur.execute("""
                INSERT INTO tucal.external_event (source, event_id, start_ts, end_ts, room_nr, group_nr, data)
                VALUES ('htu-events', %(id)s, %(start)s, %(end)s, NULL, NULL, %(data)s)
                ON CONFLICT ON CONSTRAINT pk_external_event DO
                UPDATE set start_ts = %(start)s, end_ts = %(end)s, data = %(data)s""", data)
        tucal.db.commit()

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session):
        pass
