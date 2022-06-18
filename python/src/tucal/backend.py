
from typing import Dict, Any, Optional, List, Tuple
import time
import json
import datetime
import argparse
import re
import socket
import smtplib
from email.mime.text import MIMEText

import tucal.db


SYNC_MINUTES = 6 * 60
SYNC_MAX_MINUTES = 8 * 60
SYNC_RETRY_MINUTES = 30


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

config = tucal.get_config()
SMTP_HOST = config['email']['smtp_host']
SMTP_PORT = int(config['email']['smtp_port'])
SMTP_USER = config['email']['smtp_user']
SMTP_PASSWORD = config['email']['smtp_password']
EMAIL_FROM = config['email']['from']
EMAIL_HOSTNAME = config['tucal']['hostname']

LAST_PLUGIN_SYNC: Optional[datetime.datetime] = None
PLUGIN_SYNC_INTERVAL: int = 3600


def merge_event_data(event_nr: int, data: Dict[str, Any], parent_nr: int, room_nr: int, group_nr: int, group_name: str,
                     start_ts: datetime.datetime, end_ts: datetime.datetime):
    data.update({
        'day_event': False,
        'status': None,
        'summary': None,
        'desc': None,
        'zoom': None,
        'lt': False,
        'yt': None,
        'url': None,
        'type': None,
        'mode': None,
        'tiss_url': None,
        'tuwel_url': None,
        'source_url': None,
        'source_name': None,
        'organizer': None,
    })
    if 'user' not in data:
        data['user'] = {}

    tuwel, tiss, tiss_extra, aurora, htu, holidays, tuwien = None, None, None, None, None, None, None

    # FIXME better event merge
    cur = tucal.db.cursor()
    cur.execute("SELECT data FROM tucal.external_event WHERE event_nr = %s", (event_nr,))
    rows = cur.fetch_all()
    for xdata, in rows:
        if 'tuwel' in xdata:
            tuwel = xdata['tuwel']
        if 'tiss' in xdata:
            tiss = xdata['tiss']
        if 'tiss_extra' in xdata:
            tiss_extra = xdata['tiss_extra']
        if 'aurora' in xdata:
            aurora = xdata['aurora']
        if 'htu' in xdata:
            htu = xdata['htu']
        if 'holidays' in xdata:
            holidays = xdata['holidays']
        if 'tuwien' in xdata:
            tuwien = xdata['tuwien']

    if tuwel:
        unix_ts = int(time.mktime(start_ts.timetuple()))
        data['tuwel_url'] = f'https://tuwel.tuwien.ac.at/calendar/view.php?view=day&time={unix_ts}'

        if not COURSE_NAME.match(tuwel['name']):
            if tuwel['module_name'] == 'organizer':
                data['summary'] = tuwel['name'][:tuwel['name'].rfind('(')].strip()
            else:
                data['summary'] = tuwel['name']

        for link in ZOOM_LINK.finditer(tuwel['description'] or tuwel['description_html'] or ''):
            data['zoom'] = 'https://' + link.group(1)
            data['mode'] = 'online_only'

        if tuwel['url']:
            data['url'] = tuwel['url']

        mod = tuwel['module_name']
        typ = tuwel['event_type']
        if mod == 'organizer':
            if typ == 'Appointment':
                data['type'] = 'appointment'
                name = tuwel['name'][tuwel['name'].find('/') + 1:].strip()
                if name.endswith(': Einzeltermin'):
                    name = name[:-14]
                data['summary'] = name
            elif typ == 'Instance':
                data['type'] = 'deadline'
        elif mod == 'quiz' and typ == 'close':
            data['type'] = 'assignment'
        elif mod == 'assign' and typ == 'due':
            data['type'] = 'assignment'
        elif mod == 'checkmark' and typ == 'due':
            data['type'] = 'assignment'

        if tuwel['description_html']:
            data['desc'] = tuwel['description_html']
        elif tuwel['description']:
            data['desc'] = tuwel['description']

    if tiss:
        initial_date = start_ts.strftime('%Y%m%d')
        data['tiss_url'] = f'https://tiss.tuwien.ac.at/events/personSchedule.xhtml?initialDate={initial_date}'

        type_nr = tiss['type']
        data['type'] = TISS_TYPES[type_nr]
        desc = tiss['description']

        if desc and desc != '-':
            data['summary'] = desc
            for link in ZOOM_LINK.finditer(desc):
                data['zoom'] = 'https://' + link.group(1)
            if 'VO' in desc.split(' ') or 'vorlesung' in desc.lower():
                data['type'] = 'lecture'

        if type_nr == 2 and data['summary'] and COURSE_NR.match(data['summary']):
            data['summary'] = None

        if data['summary'] and data['summary'].startswith('SPK'):
            data['type'] = None

        if room_nr is None:
            data['mode'] = 'online_only'

    if tiss_extra:
        data['summary'] = tiss_extra['name']
        if 'exam' in tiss_extra and tiss_extra['exam'] is not None:
            exam = tiss_extra['exam']
            data['type'] = 'exam'
            data['day_event'] = True
            data['tiss_url'] = tiss_extra['url']
        else:
            data['type'] = 'deadline'
            data['url'] = tiss_extra['url']

    if aurora:
        data['source_url'] = 'https://aurora.iguw.tuwien.ac.at/course/dwi/'
        data['source_name'] = 'Aurora'
        data['summary'] = aurora['summary']

        conference = aurora.get('conference', None)
        if conference is not None:
            data['zoom'] = conference

        if aurora.get('url', None):
            data['url'] = aurora['url']

        data['type'] = aurora['type'] if 'type' in aurora else 'course'
        data['mode'] = 'online_only'

        if start_ts == end_ts:
            data['type'] = 'assignment'

    if htu:
        data['source_url'] = htu['url']
        data['source_name'] = 'HTU Events'
        data['summary'] = htu['title']

        if 'attributedTo' in htu and htu['attributedTo'] is not None:
            data['organizer'] = htu['attributedTo']['name']

        if 'options' in htu and htu['options'] is not None:
            if htu['options']['isOnline']:
                data['mode'] = 'online_only'

        if htu['description']:
            data['desc'] = htu['description']
            for link in ZOOM_LINK.finditer(htu['description']):
                data['zoom'] = 'https://' + link.group(1)

    if tuwel:
        if data['type'] is None:
            data['type'] = 'course'

    if holidays:
        data['day_event'] = True
        data['summary'] = holidays['name']
        data['type'] = 'holiday'

    if tuwien:
        data['day_event'] = tuwien['day_event']
        data['summary'] = tuwien['summary']
        data['desc'] = tuwien['description']
        data['source_name'] = 'TU Events'
        data['source_url'] = tuwien['url']

    # delete redundant data['user'] keys
    data_items = {(k, v) for k, v in data.items() if v.__hash__}
    user_items = {(k, v) for k, v in data['user'].items() if v.__hash__}
    user_keys = {k for k, v in data['user'].items() if v.__hash__}
    diff_keys = {k for k, v in user_items - data_items}
    for k in user_keys - diff_keys:
        del data['user'][k]

    data.update(data['user'])

    data_json = json.dumps(data)
    cur.execute("UPDATE tucal.event SET data = %s, updated = TRUE WHERE event_nr = %s", (data_json, event_nr))


def update_events(all_events: bool = False):
    cur = tucal.db.cursor()
    cur.execute("LOCK TABLE tucal.event, tucal.external_event IN SHARE ROW EXCLUSIVE MODE")
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
    cur.execute("LOCK TABLE tucal.event, tucal.external_event IN SHARE ROW EXCLUSIVE MODE")
    cur.execute("""
        SELECT source, event_id, start_ts, end_ts, group_nr, room_nr, global
        FROM tucal.external_event
        WHERE event_nr IS NULL""")
    rows = cur.fetch_all()

    for source, evt_id, start_ts, end_ts, group_nr, room_nr, global_event in rows:
        # FIXME better equality check

        event_rows = None
        if source == 'tiss-extra':
            pass
        elif global_event and end_ts > start_ts:
            cur.execute("""
                SELECT e.event_nr, array_agg(x.source)
                FROM tucal.event e
                    LEFT JOIN tucal.external_event x ON x.event_nr = e.event_nr
                WHERE e.group_nr = %s AND
                      e.end_ts > e.start_ts AND
                      (e.room_nr IS NULL OR %s IS NULL OR coalesce(e.room_nr, -1) = coalesce(%s, -1)) AND
                      (%s - e.start_ts <= INTERVAL '30' MINUTE AND e.end_ts - %s <= INTERVAL '60' MINUTE) AND
                      e.global
                GROUP BY e.event_nr
                HAVING %s != ALL(array_agg(coalesce(x.source, '<NULL>')))""",
                        (group_nr, room_nr, room_nr, start_ts, end_ts, source))
            event_rows = cur.fetch_all()
        elif end_ts == start_ts:
            cur.execute("""
               SELECT e.event_nr, array_agg(x.source)
               FROM tucal.event e
                   LEFT JOIN tucal.external_event x ON x.event_nr = e.event_nr
               WHERE e.group_nr = %s AND
                     (e.room_nr IS NULL OR %s IS NULL OR coalesce(e.room_nr, -1) = coalesce(%s, -1)) AND
                     (e.start_ts = %s AND e.end_ts = %s) AND
                     e.global = %s AND
                     x.source IS NULL
               GROUP BY e.event_nr""",
                        (group_nr, room_nr, room_nr, start_ts, end_ts, global_event))
            event_rows = cur.fetch_all()

        if event_rows is None or len(event_rows) == 0:
            cur.execute("""
                INSERT INTO tucal.event (start_ts, end_ts, room_nr, group_nr, global)
                VALUES (%s, %s, NULL, %s, %s)
                RETURNING event_nr""", (start_ts, end_ts, group_nr, global_event))
            evt_nr = cur.fetch_all()[0][0]
        else:
            evt_nr = event_rows[0][0]

        cur.execute("UPDATE tucal.external_event SET event_nr = %s WHERE (source, event_id) = (%s, %s)",
                    (evt_nr, source, evt_id))

    tucal.db.commit()


def send_emails():
    cur = tucal.db.cursor()
    cur.execute("""
        SELECT message_nr, message_id, to_address, subject, message, reply_to_address, from_name, submit_ts
        FROM tucal.message
        WHERE send_ts IS NULL""")
    rows = cur.fetch_all()
    if len(rows) == 0:
        cur.close()
        return

    cur.execute("""
        SELECT DISTINCT email_address_1
        FROM tucal.v_account
        WHERE verified = TRUE AND email_address_1 IS NOT NULL""")
    addresses = [address for address, in cur.fetch_all()]

    msgs = []
    for msg_nr, msg_id, to, subj, content, reply_to, from_name, submit in rows:
        msg = MIMEText(content, 'plain', 'UTF-8')
        msg['From'] = f'{from_name or "TUcal"} <{EMAIL_FROM}>'
        msg['Date'] = submit.strftime('%a, %d %b %Y %H:%M:%S %z')
        msg['Message-ID'] = f'{msg_id}@{EMAIL_HOSTNAME}'
        msg['Subject'] = subj
        to_addresses = []
        if to:
            msg['To'] = to
            to_addresses.append(to)
        else:
            to_addresses += addresses
        if reply_to:
            msg['Reply-To'] = reply_to
        msgs.append((msg_nr, msg, to_addresses))

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    print(f'Connected to SMTP host {SMTP_HOST}:{SMTP_PORT} ({SMTP_USER})', flush=True)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    for msg_nr, msg, to_addresses in msgs:
        server.send_message(msg, to_addrs=to_addresses)
        cur.execute("UPDATE tucal.message SET send_ts = now() WHERE message_nr = %s", (msg_nr,))
        print(f'Sent Msg#{msg_nr}', flush=True)

    server.quit()
    cur.close()


def clear_invalid_tokens():
    cur = tucal.db.cursor()
    cur.execute("DELETE FROM tucal.token WHERE valid_ts < now()")
    cur.close()


def schedule_job(job_args: List[str], delay: int = 0) -> Tuple[int, str, Optional[int]]:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect('/var/tucal/scheduler.sock')
    except FileNotFoundError:
        raise RuntimeError('unable to contact scheduler')
    client.send((' '.join([str(delay)] + job_args) + '\n').encode('utf8'))

    res = client.recv(256).decode('utf8')
    if res.startswith('error:'):
        client.close()
        del client
        raise RuntimeError(res[6:].strip())

    lines = res.split('\n')
    res_parts = lines[0].strip().split(' ')
    pid = None
    if len(lines) > 1 and len(lines[1].strip()) > 0:
        pid = int(lines[1])
    elif delay < 1:
        res = client.recv(256).decode('utf8')
        lines += res.split('\n')
        pid = lines[1].strip()
        pid = int(pid) if len(pid) > 0 else None

    client.close()
    del client

    # job_nr, job_id, pid
    return int(res_parts[0]), res_parts[1], pid


def sync_users():
    cur = tucal.db.cursor()
    cur.execute("SELECT SUM(sso_credentials::int), MIN(EXTRACT(EPOCH FROM (now() - sync_try_ts))) FROM tucal.v_account")
    row = cur.fetch_all()[0]
    num_users, last_sync_diff = row[0], float(row[1])
    sync_interval = SYNC_MINUTES / num_users * 60

    cur.execute(f"""
        SELECT a.mnr, EXTRACT(EPOCH FROM (now() - a.sync_try_ts)) AS diff
        FROM tucal.v_account a
            LEFT JOIN tucal.v_job j ON (j.mnr = a.mnr AND j.name = 'sync user')
        WHERE (a.sync_ts IS NULL OR a.sync_ts < now() - INTERVAL '{SYNC_MINUTES} minutes') AND
              (a.sync_try_ts IS NULL OR a.sync_try_ts < now() - INTERVAL '{SYNC_RETRY_MINUTES} minutes') AND
              a.sso_credentials = TRUE
        GROUP BY a.mnr, a.sync_ts, a.sync_try_ts, j.mnr
        HAVING (NOT ('running' = ANY(array_agg(j.status)) OR 'waiting' = ANY(array_agg(j.status)))) OR
               j.mnr IS NULL
        ORDER BY a.sync_try_ts""")
    rows = cur.fetch_all()
    if len(rows) == 0:
        return

    time_usable = (rows[0][1] or 0) - (rows[-1][1] or 0) + (SYNC_MAX_MINUTES - SYNC_MINUTES) * 60
    sync_interval_usable = time_usable / len(rows)

    cur_sync_interval = min(sync_interval, sync_interval_usable)
    cur_delay = max(0.0, cur_sync_interval - last_sync_diff)

    for mnr, diff in rows:
        delay = min(cur_delay, SYNC_MAX_MINUTES * 60 - float(diff or 0))
        print(f'Syncing user {mnr}... (delay {delay / 60:.1f}m)', flush=True)
        try:
            job_nr, job_id, pid = schedule_job(['sync-user', 'keep', str(mnr)], delay=int(delay))
            print(f'Informed scheduler: {job_nr} {job_id} (PID {pid})', flush=True)
        except RuntimeError as e:
            print(f'Error: {e}', flush=True)
        cur_delay += cur_sync_interval


def sync_plugins():
    global LAST_PLUGIN_SYNC
    now = tucal.now()
    if LAST_PLUGIN_SYNC is None or (now - LAST_PLUGIN_SYNC).total_seconds() > PLUGIN_SYNC_INTERVAL:
        print('Syncing plugins...', flush=True)
        try:
            job_nr, job_id, pid = schedule_job(['sync-plugins'])
            print(f'Informed scheduler: {job_nr} {job_id} (PID {pid})', flush=True)
            LAST_PLUGIN_SYNC = now
        except RuntimeError as e:
            print(f'Error: {e}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mx = parser.add_mutually_exclusive_group()
    mx.add_argument('-u', '--update', required=False, action='store_true')
    mx.add_argument('-s', '--skip-updates', required=False, action='store_true')
    args = parser.parse_args()

    if not args.skip_updates:
        print('Updating all events...', flush=True)
        update_events(all_events=True)
        print('Successfully updated all events', flush=True)
        if args.update:
            exit(0)

    print('Starting main loop', flush=True)
    while True:
        sync_plugins()
        send_emails()
        merge_external_events()
        update_events()
        clear_invalid_tokens()
        sync_users()
        time.sleep(1)
