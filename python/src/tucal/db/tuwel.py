
from typing import Dict, Any, List
import datetime

import tucal.icalendar as ical
import tucal.db as db


def upsert_ical_events(events: List[ical.Event], user_id: int = None):
    cur = db.cursor()

    cur.execute("SELECT event_id FROM tuwel.event")
    evt_ids = [evt[0] for evt in cur.fetch_all()]

    rows_insert = []
    rows_update = []
    for evt in events:
        data = {
            'id': int(evt.uid.split('@')[0]),
            'short': evt.categories[0],
            'start': evt.start,
            'end': evt.end,
            'access': evt.access,
            'mod': evt.last_modified,
            'name': evt.summary,
            'desc': evt.description,
        }

        if data['id'] in evt_ids:
            rows_update.append(data)
        else:
            rows_insert.append(data)

    if len(rows_insert) > 0:
        cur.execute_values("""
            INSERT INTO tuwel.event (event_id, course_id, start_ts, end_ts, access_ts, mod_ts, name, description)
            VALUES (%(id)s, (SELECT course_id FROM tuwel.course WHERE short = %(short)s), %(start)s, %(end)s,
                    %(access)s, %(mod)s, %(name)s, %(desc)s)""", rows_insert)

    if len(rows_update) > 0:
        cur.execute_values("""
            UPDATE tuwel.event e
            SET start_ts = d.start_ts, end_ts = d.end_ts, access_ts = d.acc, mod_ts = d.mod,
                name = d.name, description = d.description
            FROM (VALUES (%(id)s, %(start)s, %(end)s, %(access)s, %(mod)s, %(name)s, %(desc)s)) AS
                d (id, start_ts, end_ts, acc, mod, name, description)
            WHERE e.event_id = d.id""", rows_update)

    if user_id is not None:
        cur.execute_values("""
            INSERT INTO tuwel.event_user (event_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING""", [(evt['id'], user_id) for evt in rows_insert + rows_update])

    cur.close()


def upsert_events(events: List[Dict[str, Any]], access_time: datetime.datetime, user_id: int = None):
    cur = db.cursor()

    cur.execute("SELECT event_id FROM tuwel.event")
    evt_ids = [evt[0] for evt in cur.fetch_all()]

    rows_insert = []
    rows_update = []
    for evt in events:
        start = datetime.datetime.fromtimestamp(evt['timestart']).astimezone()
        data = {
            'id': evt['id'],
            'name': evt['name'],
            'course': evt['course']['id'],
            'start': start,
            'end': start + datetime.timedelta(seconds=evt['timeduration']),
            'mod': datetime.datetime.fromtimestamp(evt['timemodified']).astimezone(),
            'access': access_time,
            'user': user_id,
            'desc': None,
            'desc_html': None,
            'loc': None,
            'url': None,
            'module': None,
            'component': None,
            'type': None,
            'f_action': evt.get('isactionevent', None),
            'f_course': evt.get('iscourseevent', None),
            'f_cat': evt.get('iscategoryevent', None),
        }

        desc = evt.get('description', None)
        if desc and len(desc) > 0:
            if evt.get('descriptionformat', None) == 1:
                data['desc_html'] = desc
            else:
                data['desc'] = desc

        loc = evt.get('location', None)
        if loc and len(loc) > 0:
            data['loc'] = loc

        url = evt.get('url', None)
        if url and len(url) > 0:
            data['url'] = url

        mod = evt.get('modulename', None)
        if mod and len(mod) > 0:
            data['module'] = mod

        comp = evt.get('component', None)
        if comp and len(comp) > 0:
            data['component'] = comp

        evt_type = evt.get('eventtype', None)
        if evt_type and len(evt_type) > 0:
            data['type'] = evt_type

        if data['id'] in evt_ids:
            rows_update.append(data)
        else:
            rows_insert.append(data)

    if len(rows_insert) > 0:
        cur.execute_values("""
            INSERT INTO tuwel.event (event_id, course_id, start_ts, end_ts, access_ts, mod_ts, name, description,
                                     description_html, url, location, module_name, component, event_type,
                                     f_action_event, f_course_event, f_category_event)
            VALUES (%(id)s, %(course)s, %(start)s, %(end)s, %(access)s, %(mod)s, %(name)s, %(desc)s, %(desc_html)s,
                    %(url)s, %(loc)s, %(module)s, %(component)s, %(type)s, %(f_action)s, %(f_course)s,
                    %(f_cat)s)""", rows_insert)

    if len(rows_update) > 0:
        cur.execute_values("""
            UPDATE tuwel.event e
            SET start_ts = d.start_ts, end_ts = d.end_ts, access_ts = d.acc, mod_ts = d.mod, name = d.name,
                description = COALESCE(d.description, e.description),
                description_html = COALESCE(d.desc_html, e.description_html),
                url = COALESCE(d.url, e.url),
                location = COALESCE(d.loc, e.location),
                module_name = COALESCE(d.module, e.module_name),
                component = COALESCE(d.comp, e.component),
                event_type = COALESCE(d.type, e.event_type),
                f_action_event = COALESCE(d.f_action, e.f_action_event),
                f_course_event = COALESCE(d.f_course, e.f_course_event),
                f_category_event = COALESCE(d.f_cat, e.f_category_event)
            FROM (VALUES (%(id)s, %(start)s, %(end)s, %(access)s, %(mod)s, %(name)s, %(desc)s,
                          %(desc_html)s,%(url)s, %(loc)s, %(module)s, %(component)s, %(type)s, %(f_action)s,
                          %(f_course)s, %(f_cat)s)) AS
                d (id, start_ts, end_ts, acc, mod, name, description, desc_html, url, loc, module, comp, type, f_action,
                   f_course, f_cat)
            WHERE e.event_id = d.id""", rows_update)

    if user_id is not None:
        cur.execute_values("""
            INSERT INTO tuwel.event_user (event_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING""", [(evt['id'], user_id) for evt in (rows_insert + rows_update)])

    cur.close()
    return

