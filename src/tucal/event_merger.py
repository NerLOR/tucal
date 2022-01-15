
from typing import Dict, Any
import time
import json
import datetime
import argparse
import re

import tucal.db


ZOOM_LINK = re.compile(r'https?://([a-z]*\.zoom\.us[A-Za-z0-9/?=]*)')
COURSE_NAME = re.compile(r'^[0-9]{3}\.[0-9A-Z]{3} .*? \([A-Z]{2} [0-9],[0-9]\) [0-9]{4}[WS]$')
COURSE_NR = re.compile(r'^[0-9]{3}\.[0-9A-Z]{3} ')

TISS_TYPES = {
    0: 'general',
    1: 'course',
    2: 'group',
    3: 'exam',
    4: None,
    5: 'roomTUlearn',
}


def merge_event_data(event_nr: int, data: Dict[str, Any], parent_nr: int, room_nr: int, group_nr: int, group_name: str,
                     start_ts: datetime.datetime, end_ts: datetime.datetime):
    data.update({
        'summary': None,
        'desc': None,
        'zoom': None,
        'lt': None,
        'url': None,
        'type': None,
        'online': None,
        'tiss_url': None,
        'tuwel_url': None,
        'source_url': None,
        'source_name': None,
        'organizer': None,
    })
    if 'user' not in data:
        data['user'] = {}

    tuwel, tiss, aurora, htu = None, None, None, None

    # FIXME better event merge
    cur = tucal.db.cursor()
    cur.execute("SELECT data FROM tucal.external_event WHERE event_nr = %s", (event_nr,))
    rows = cur.fetch_all()
    for xdata, in rows:
        if 'tuwel' in xdata:
            tuwel = xdata['tuwel']
        if 'tiss' in xdata:
            tiss = xdata['tiss']
        if 'aurora' in xdata:
            aurora = xdata['aurora']
        if 'htu' in xdata:
            htu = xdata['htu']

    if tuwel:
        unix_ts = time.mktime(start_ts.timetuple())
        data['tuwel_url'] = f'https://tuwel.tuwien.ac.at/calendar/view.php?view=day&time={unix_ts}'

        if not COURSE_NAME.match(tuwel['name']):
            data['summary'] = tuwel['name']

        for link in ZOOM_LINK.finditer(tuwel.get('desc', None) or tuwel.get('desc_html', None) or ''):
            data['zoom'] = 'https://' + link.group(1)
            data['online'] = True

        if 'url' in tuwel:
            data['url'] = tuwel['url']

        if 'desc_html' in tuwel:
            data['desc'] = tuwel['desc_html']
        elif 'desc' in tuwel:
            data['desc'] = tuwel['desc']

    if tiss:
        initial_date = start_ts.strftime('%Y%m%d')
        data['tiss_url'] = f'https://tiss.tuwien.ac.at/events/personSchedule.xhtml?initialDate={initial_date}'

        type_nr = tiss['type']
        data['type'] = TISS_TYPES[type_nr]
        desc = tiss['description']

        if desc and desc != '-':
            data['summary'] = desc

        if data['summary']:
            if 'VO' in data['summary'].split(' ') or 'vorlesung' in data['summary'].lower():
                data['type'] = 'lecture'

        if type_nr == 2 and data['summary'] and COURSE_NR.match(data['summary']):
            data['summary'] = None

        if data['summary'] and data['summary'].startswith('SPK'):
            data['type'] = None

        if room_nr is None:
            data['online'] = True

    if aurora:
        data['source_url'] = 'https://aurora.iguw.tuwien.ac.at/course/dwi/'
        data['source_name'] = 'Aurora'
        data['summary'] = aurora['summary']

        conference = aurora.get('conference', None)
        if conference is not None:
            data['zoom'] = conference

        url = aurora.get('url', None)
        if url is not None:
            data['url'] = url

        data['type'] = aurora['type'] if 'type' in aurora else 'course'
        data['online'] = True

    if htu:
        data['source_url'] = htu['url']
        data['source_name'] = 'HTU Events'
        data['summary'] = htu['title']
        data['desc'] = htu['description']

        if 'attributedTo' in htu and htu['attributedTo'] is not None:
            data['organizer'] = htu['attributedTo']['name']

        if 'options' in htu and htu['options'] is not None:
            data['online'] = htu['options']['isOnline']

        for link in ZOOM_LINK.finditer(htu.get('description', '')):
            data['zoom'] = 'https://' + link.group(1)

        if data['online'] is None:
            data['online'] = (data['zoom'] is not None)

    if start_ts == end_ts:
        data['type'] = 'due'

    data.update(data['user'])

    data_json = json.dumps(data)
    cur.execute("UPDATE tucal.event SET data = %s, updated = TRUE WHERE event_nr = %s", (data_json, event_nr))


def update_events(all_events: bool = False):
    cur = tucal.db.cursor()
    cur.execute("LOCK TABLE tucal.event IN SHARE ROW EXCLUSIVE MODE")
    cur.execute("""
        SELECT e.event_nr, e.data, e.parent_event_nr, e.start_ts, e.end_ts, e.room_nr, e.group_nr, l.name
        FROM tucal.event e
            LEFT JOIN tucal.group_link l ON l.group_nr = e.group_nr
        WHERE updated = ANY(%s)""", ([False, all_events],))
    rows = cur.fetch_all()
    for event_nr, data, parent_nr, start_ts, end_ts, room_nr, group_nr, group_name in rows:
        merge_event_data(event_nr, data, parent_nr, room_nr, group_nr, group_name, start_ts, end_ts)
    tucal.db.commit()


def merge_external_events():
    cur = tucal.db.cursor()
    cur.execute("LOCK TABLE tucal.event IN SHARE ROW EXCLUSIVE MODE")
    cur.execute("""
        SELECT source, event_id, start_ts, end_ts, group_nr
        FROM tucal.external_event
        WHERE event_nr IS NULL""")
    rows = cur.fetch_all()

    for source, evt_id, start_ts, end_ts, group_nr in rows:
        # FIXME better equality check
        cur.execute("""
            SELECT e.event_nr, array_agg(x.source)
            FROM tucal.event e
                LEFT JOIN tucal.external_event x ON x.event_nr = e.event_nr
            WHERE e.group_nr = %s AND
                  (%s - e.start_ts <= INTERVAL '30' MINUTE AND e.end_ts - %s <= INTERVAL '60' MINUTE)
            GROUP BY e.event_nr""", (group_nr, start_ts, end_ts))
        event_rows = cur.fetch_all()
        event_rows = [(evt_nr, sources) for evt_nr, sources in event_rows if source not in sources]

        if len(event_rows) == 0:
            cur.execute("""
                INSERT INTO tucal.event (start_ts, end_ts, room_nr, group_nr)
                VALUES (%s, %s, NULL, %s)
                RETURNING event_nr""", (start_ts, end_ts, group_nr))
            evt_nr = cur.fetch_all()[0][0]
        else:
            evt_nr = event_rows[0][0]

        print(f'{source}/{evt_id} -> {evt_nr}')
        cur.execute("UPDATE tucal.external_event SET event_nr = %s WHERE (source, event_id) = (%s, %s)",
                    (evt_nr, source, evt_id))

    tucal.db.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--update', required=False, action='store_true')
    args = parser.parse_args()

    update_events(all_events=True)

    if args.update:
        exit(0)

    while True:
        merge_external_events()
        update_events()
        time.sleep(1)
