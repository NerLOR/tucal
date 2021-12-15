
import typing
import time
import json

import tucal.db


def update_event(events: typing.List[typing.Dict[str, typing.Any]]):
    evt = {
        'summary': None,
        'desc': None,
        'details': None
    }
    # FIXME better event merge
    for ext in events:
        if ext is None:
            continue
        evt.update(ext)
    if 'tuwel' in evt:
        evt['summary'] = evt['tuwel']['name']
    if 'aurora' in evt:
        evt['summary'] = evt['aurora']['summary']
    if 'eventHTU' in evt:
        evt['summary'] = evt['eventHTU']['title']
    return evt


if __name__ == '__main__':
    cur = tucal.db.cursor()

    cur.execute("""
        SELECT e.event_nr, array_agg(x.data) FROM tucal.event e
        LEFT JOIN tucal.external_event x ON x.event_nr = e.event_nr
        GROUP BY e.event_nr""")
    rows = cur.fetchall()
    for event_nr, datas in rows:
        data = json.dumps(update_event(datas))
        cur.execute("UPDATE tucal.event SET data = %s, updated = TRUE WHERE event_nr = %s", (data, event_nr))
    tucal.db.commit()

    while True:
        cur.execute("""
            SELECT x.source, x.event_id, e.event_nr, x.start_ts, x.end_ts, x.group_nr FROM tucal.external_event x 
            LEFT JOIN tucal.event e ON (e.group_nr, e.start_ts) = (x.group_nr, x.start_ts)
            WHERE x.event_nr IS NULL""")
        rows = cur.fetchall()
        for source, evt_id, evt_nr, start, end, group in rows:
            # FIXME better equality check
            if evt_nr is None:
                cur.execute("""
                    INSERT INTO tucal.event (start_ts, end_ts, room_nr, group_nr)
                    VALUES (%s, %s, NULL, %s) RETURNING event_nr""", (start, end, group))
                evt_nr = cur.fetchall()[0][0]
            print(source, evt_id, evt_nr)
            cur.execute("UPDATE tucal.external_event SET event_nr = %s WHERE (source, event_id) = (%s, %s)",
                        (evt_nr, source, evt_id))
        tucal.db.commit()

        cur.execute("""
               SELECT e.event_nr, array_agg(x.data) FROM tucal.event e
               LEFT JOIN tucal.external_event x ON x.event_nr = e.event_nr
               WHERE e.updated = FALSE
               GROUP BY e.event_nr""")
        rows = cur.fetchall()
        for event_nr, datas in rows:
            data = json.dumps(update_event(datas))
            cur.execute("UPDATE tucal.event SET data = %s, updated = TRUE WHERE event_nr = %s", (data, event_nr))
        tucal.db.commit()

        time.sleep(1)
