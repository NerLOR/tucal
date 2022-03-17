
from typing import Dict, Any
import datetime

import tucal.icalendar as ical
import tucal.db as db


def upsert_ical_event(evt: ical.Event, user_id: int = None):
    cur = db.cursor()

    data = {
        'id': evt.uid.split('@')[0],
        'short': evt.categories[0],
        'start': evt.start,
        'end': evt.end,
        'access': evt.access,
        'mod': evt.last_modified,
        'name': evt.summary,
        'desc': evt.description,
        'user': user_id
    }

    cur.execute("""
        INSERT INTO tuwel.event (event_id, course_id, start_ts, end_ts, access_ts, mod_ts, name, description)
        VALUES (%(id)s, (SELECT course_id FROM tuwel.course WHERE short = %(short)s), %(start)s, %(end)s, %(access)s,
        %(mod)s, %(name)s, %(desc)s)
        ON CONFLICT ON CONSTRAINT pk_event DO UPDATE
        SET start_ts = %(start)s, end_ts = %(end)s, access_ts = %(access)s, mod_ts = %(mod)s, name = %(name)s,
            description = %(desc)s""", data)

    if user_id is not None:
        cur.execute("""
            INSERT INTO tuwel.event_user (event_id, user_id) 
            VALUES (%(id)s, %(user)s)
            ON CONFLICT DO NOTHING""", data)

    cur.close()


def upsert_event(evt: Dict[str, Any], access_time: datetime.datetime, user_id: int = None):
    cur = db.cursor()

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

    cur.execute("""
        INSERT INTO tuwel.event (event_id, course_id, start_ts, end_ts, access_ts, mod_ts, name, description,
                                 description_html, url, location, module_name, component, event_type, f_action_event,
                                 f_course_event, f_category_event)
        VALUES (%(id)s, %(course)s, %(start)s, %(end)s, %(access)s, %(mod)s, %(name)s, %(desc)s, %(desc_html)s,
                %(url)s, %(loc)s, %(module)s, %(component)s, %(type)s, %(f_action)s, %(f_course)s, %(f_cat)s)
        ON CONFLICT ON CONSTRAINT pk_event DO UPDATE
        SET start_ts = %(start)s, end_ts = %(end)s, access_ts = %(access)s, mod_ts = %(mod)s, name = %(name)s,
            description = COALESCE(%(desc)s, event.description),
            description_html = COALESCE(%(desc_html)s, event.description_html),
            url = COALESCE(%(url)s, event.url),
            location = COALESCE(%(loc)s, event.location),
            module_name = COALESCE(%(module)s, event.module_name),
            component = COALESCE(%(component)s, event.component),
            event_type = COALESCE(%(type)s, event.event_type),
            f_action_event = COALESCE(%(f_action)s, event.f_action_event),
            f_course_event = COALESCE(%(f_course)s, event.f_course_event),
            f_category_event = COALESCE(%(f_cat)s, event.f_category_event)""", data)

    if user_id is not None:
        cur.execute("""
            INSERT INTO tuwel.event_user (event_id, user_id)
            VALUES (%(id)s, %(user)s)
            ON CONFLICT ON CONSTRAINT pk_event_user DO NOTHING""", data)

    cur.close()
    return

