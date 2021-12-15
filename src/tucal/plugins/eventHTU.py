import requests
import json

import tucal
import tucal.db
import tuwien.sso

query = {
  "operationName": "FetchEvents",
  "variables": {
    "page": 1,
    "limit": 50
  },
  "query": "query FetchEvents($orderBy: EventOrderBy, $direction: SortDirection, $page: Int, $limit: Int) { events(orderBy: $orderBy, direction: $direction, page: $page, limit: $limit) { total elements { id url title description beginsOn endsOn status picture { id url } physicalAddress { id description locality } tags { ...TagFragment } } }} fragment TagFragment on Tag { id title}"
}

HTU_HOST = 'events.htu.at'
HTU = f'https://{HTU_HOST}'


class EVENTS(tucal.Plugin):
    @staticmethod
    def sync():
        url = f'{HTU}/api'
        r = requests.post(url, json=query)
        if r.status_code != 200:
            raise RuntimeError()

        cur = tucal.db.cursor()

        raw_events = r.json()
        events = raw_events['data']['events']['elements']

        for event in events:
            data = {
                'id': f'htu-{event["id"]}',
                'start': event['beginsOn'],
                'end': event['endsOn'],
                'room': event['url'],
                'del': not (event['status'] == 'CONFIRMED'),
                'data': json.dumps(event)
            }

            cur.execute("""
                INSERT INTO tucal.external_event (source, event_id, start_ts, end_ts, room_nr, group_nr, data, deleted)
                VALUES ('eventHTU', %(id)s, %(start)s, %(end)s, %(room)s, NULL, %(data)s, %(del)s)
                ON CONFLICT ON CONSTRAINT pk_external_event DO
                UPDATE set start_ts = %(start)s, end_ts = %(end)s, room_nr = %(room)s, group_nr = NULL,
                           data = %(data)s, deleted = %(del)s""", data)
        tucal.db.commit()

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session):
        EVENTS.sync()
