
from typing import List, Dict, Any
import time
import json
import datetime
import argparse
import re

import tucal.db


ZOOM_LINK = re.compile(r'https?://([a-z]*\.zoom\.us[A-Za-z0-9/?=]*)')
COURSE_NAME = re.compile(r'^[0-9]{3}\.[0-9A-Z]{3} .*? \([A-Z]{2} [0-9],[0-9]\) [0-9]{4}[WS]$')

TYPES = {
    0: 'general',
    1: 'course',
    2: 'group',
    3: 'exam',
    4: None,
    5: 'roomTUlearn',
}


def update_event(events: List[Dict[str, Any]], start: datetime.datetime, end: datetime.datetime, room: int):
    evt = {
        'summary': None,
        'desc': None,
        'details': None,
        'zoom': None,
        'lt': None,
        'url': None,
        'type': None,
    }
    # FIXME better event merge
    for ext in events:
        if ext is None:
            continue
        for k1, v1 in ext.items():
            if k1 in evt:
                v1 = {k2: v2 for k2, v2 in v1.items() if v2 is not None}
                evt[k1].update(v1)
            else:
                evt[k1] = v1
    if 'tuwel' in evt:
        if not COURSE_NAME.match(evt['tuwel']['name']):
            evt['summary'] = evt['tuwel']['name']
        for link in ZOOM_LINK.finditer(evt['tuwel'].get('desc', None) or evt['tuwel'].get('desc_html', None) or ''):
            evt['zoom'] = 'https://' + link.group(1)
        if 'url' in evt['tuwel']:
            evt['url'] = evt['tuwel']['url']
    if 'tiss' in evt:
        type_nr = evt['tiss']['type']
        evt['type'] = TYPES[type_nr]
        desc = evt['tiss']['description']
        if desc and desc != '-':
            evt['summary'] = desc
    if 'aurora' in evt:
        evt['summary'] = evt['aurora']['summary']
        url = evt['aurora'].get('url', None)
        if url is not None:
            evt['zoom'] = url
        evt['type'] = 'course'
    if 'htu' in evt:
        evt['summary'] = evt['htu']['title']
    if start == end:
        evt['type'] = 'due'
    return evt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--once', required=False, action='store_true')
    args = parser.parse_args()

    cur = tucal.db.cursor()

    cur.execute("""
        SELECT e.event_nr, array_agg(x.data), e.start_ts, e.end_ts, e.room_nr
        FROM tucal.event e
        LEFT JOIN tucal.external_event x ON x.event_nr = e.event_nr
        GROUP BY e.event_nr""")
    rows = cur.fetch_all()
    for event_nr, datas, start_ts, end_ts, room_nr in rows:
        data = update_event(datas, start_ts, end_ts, room_nr)
        data_json = json.dumps(data)
        cur.execute("UPDATE tucal.event SET data = %s, updated = TRUE WHERE event_nr = %s", (data_json, event_nr))
    tucal.db.commit()

    if args.once:
        exit(0)

    while True:
        cur.execute("""
            SELECT source, event_id, start_ts, end_ts, group_nr
            FROM tucal.external_event
            WHERE event_nr IS NULL""")
        rows = cur.fetch_all()
        for source, evt_id, start, end, group in rows:
            # FIXME better equality check
            cur.execute("""
                SELECT e.event_nr, array_agg(x.source)
                FROM tucal.event e
                LEFT JOIN tucal.external_event x ON x.event_nr = e.event_nr
                WHERE e.group_nr = %s AND 
                      (%s - e.start_ts <= INTERVAL '30' MINUTE AND e.end_ts - %s <= INTERVAL '60' MINUTE)
                GROUP BY e.event_nr""", (group, start, end))
            event_rows = cur.fetch_all()
            event_rows = [(evt_nr, sources) for evt_nr, sources in event_rows if source not in sources]
            if len(event_rows) == 0:
                cur.execute("""
                    INSERT INTO tucal.event (start_ts, end_ts, room_nr, group_nr)
                    VALUES (%s, %s, NULL, %s) RETURNING event_nr""", (start, end, group))
                evt_nr = cur.fetch_all()[0][0]
            else:
                evt_nr = event_rows[0][0]
            print(f'{source}/{evt_id} -> {evt_nr}')
            cur.execute("UPDATE tucal.external_event SET event_nr = %s WHERE (source, event_id) = (%s, %s)",
                        (evt_nr, source, evt_id))
        tucal.db.commit()

        cur.execute("""
            SELECT e.event_nr, array_agg(x.data), e.start_ts, e.end_ts, e.room_nr
            FROM tucal.event e
            LEFT JOIN tucal.external_event x ON x.event_nr = e.event_nr
            WHERE e.updated = FALSE
            GROUP BY e.event_nr""")
        rows = cur.fetch_all()
        for event_nr, datas, start_ts, end_ts, room_nr in rows:
            data = update_event(datas, start_ts, end_ts, room_nr)
            data_json = json.dumps(data)
            cur.execute("UPDATE tucal.event SET data = %s, updated = TRUE WHERE event_nr = %s", (data_json, event_nr))
        tucal.db.commit()

        time.sleep(1)
