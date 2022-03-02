
import argparse
import base64
import random
import time
import hmac
import struct
import json

from tucal import Job
import tucal.plugins
import tuwien.tuwel
import tuwien.tiss
import tuwien.sso
import tucal.db
import tucal.db.tiss
import tucal.db.tuwel
from tucal.jobs.sync_cal import sync_cal


TUWEL_INIT_VAL = 2
TUWEL_GROUP_VAL = 20
TUWEL_MONTHS_PRE = 12
TUWEL_MONTHS_POST = 6
TUWEL_MONTHS = TUWEL_MONTHS_PRE + TUWEL_MONTHS_POST
TUWEL_MONTH_VAL = 2
TISS_VAL_1 = 5
TISS_VAL_2 = 15
SYNC_CAL_VAL = 10
SYNC_PLUGIN_VAL = 10


def totp_gen_token(gen: bytes, mode: str = 'sha1') -> str:
    t = int(time.time() / 30)
    msg = struct.pack('>Q', t)
    val = hmac.digest(gen, msg, mode)

    offset = val[-1] & 0x0F
    (num,) = struct.unpack('>I', val[offset:offset + 4])
    num &= 0x7F_FF_FF_FF

    otp = num % 1_000_000
    return f'{otp:06}'


def enc(plain: bytes, key: int) -> str:
    cipher = bytearray(plain)
    for i in range(len(cipher)):
        cipher[i] = (cipher[i] + key) % 256
        key += 3
    return base64.b64encode(cipher).decode('ascii')


def dec(cipher: str, key: int) -> bytes:
    plain = bytearray(base64.b64decode(cipher.encode('ascii')))
    for i in range(len(plain)):
        plain[i] = (plain[i] - key + 256) % 256
        key += 3
    return plain


def sync_user(mnr: int, use_db: bool = False, store_db: bool = False, keep_tiss_cal_settings: bool = False,
              job: Job = None):
    cur = tucal.db.cursor()

    now = tucal.now()
    val = TUWEL_MONTHS * TUWEL_MONTH_VAL + TUWEL_INIT_VAL + TUWEL_GROUP_VAL + TISS_VAL_1 + TISS_VAL_2 + \
        SYNC_CAL_VAL + SYNC_PLUGIN_VAL

    job = job or Job()
    job.init('sync user', 4, val, estimate=50)

    mnr = f'{mnr:08}'
    tfa_token = None
    tfa_gen = None
    if not use_db:
        pwd = input()
        try:
            tfa = input()
            tfa = None if len(tfa) == 0 else tfa.replace(' ', '')
            if tfa and len(tfa) <= 6:
                tfa_token = tfa
            elif tfa:
                tfa_gen = base64.b64decode(tfa)
        except EOFError:
            pass
    else:
        cur.execute("""
            SELECT key, pwd, tfa_gen FROM tucal.sso_credential
            WHERE account_nr = (SELECT account_nr FROM tucal.account WHERE mnr = %s)""", (mnr,))
        cred = cur.fetch_all()
        if len(cred) == 0:
            raise RuntimeError('account credentials not found in database')
        acc_key, pwd_enc, tfa_gen_enc = cred[0]
        pwd = dec(pwd_enc, acc_key).decode('utf8')
        tfa_gen = dec(tfa_gen_enc, acc_key) if tfa_gen_enc is not None else None

    if tfa_token is None and tfa_gen is not None:
        tfa_token = totp_gen_token(tfa_gen)

    sso = tuwien.sso.Session()
    sso.credentials(mnr, pwd, tfa_token)

    job.begin('sync tiss', 2)
    job.begin('login tiss')
    tiss = tuwien.tiss.Session(sso)

    try:
        tiss.sso_login()
    except tucal.InvalidCredentialsError as e:
        if use_db:
            cur.execute("""
                DELETE FROM tucal.sso_credential
                WHERE account_nr = (SELECT account_nr FROM tucal.account WHERE mnr = %s)""", (mnr,))
            tucal.db.commit()
        raise e
    job.end(TISS_VAL_1)

    job.begin('sync tiss user courses')
    cur.execute("UPDATE tucal.account SET verified = TRUE WHERE mnr = %s", (mnr,))
    if store_db:
        acc_key = random.randint(10, 200)
        pwd_enc = enc(pwd.encode('utf8'), acc_key)
        tfa_gen_enc = enc(tfa_gen, acc_key) if tfa_gen is not None else None
        data = {
            'mnr': mnr,
            'key': acc_key,
            'pwd': pwd_enc,
            'tfa_gen': tfa_gen_enc,
        }
        cur.execute("""
            INSERT INTO tucal.sso_credential (account_nr, key, pwd, tfa_gen)
            VALUES ((SELECT account_nr FROM tucal.account WHERE mnr = %(mnr)s), %(key)s, %(pwd)s, %(tfa_gen)s)
            ON CONFLICT ON CONSTRAINT pk_sso_credential DO UPDATE
            SET key = %(key)s, pwd = %(pwd)s, tfa_gen = %(tfa_gen)s""", data)

    tucal.db.commit()

    tiss_cal_token = tiss.calendar_token
    data = {
        'mnr': mnr,
        'token': tiss_cal_token,
    }
    cur.execute("""
        INSERT INTO tiss.user (mnr, auth_token) VALUES (%(mnr)s, %(token)s)
        ON CONFLICT ON CONSTRAINT pk_user DO UPDATE
        SET auth_token = %(token)s""", data)

    tucal.db.commit()

    favorites = tiss.favorites
    course_events = {}
    course_groups = {}
    course_due_events = {}
    for course in favorites:
        if course.semester < tucal.Semester.last():
            continue
        course_events[course] = tiss.get_course_events(course)
        course_groups[course] = tiss.get_groups(course)
        course_due_events[course] = tiss.get_course_due_events(course)

    cur.execute("DELETE FROM tiss.course_user WHERE mnr = %s", (mnr,))
    cur.execute("""
        DELETE FROM tiss.group_user u
        WHERE u.mnr = %s AND
        (SELECT g.deregistration_end > now() FROM tiss.group g
            WHERE (g.course_nr, g.semester, g.group_name) = (u.course_nr, u.semester, u.group_name))""", (mnr,))
    cur.execute("""
        DELETE FROM tiss.exam_user u
        WHERE mnr = %s AND
        (SELECT e.deregistration_end > now() FROM tiss.exam e
            WHERE (e.course_nr, e.semester, e.exam_name) = (u.course_nr, u.semester, u.exam_name))""", (mnr,))

    cur.execute_values("INSERT INTO tiss.course_user (course_nr, semester, mnr) VALUES (%s, %s, %s)",
                       [(course.nr, str(course.semester), mnr) for course in favorites])

    for course, events in course_events.items():
        tucal.db.tiss.upsert_course_events(events, course, access_time=now, mnr=int(mnr))

    for course, groups in course_groups.items():
        rows = [{
            'nr': course.nr,
            'sem': str(course.semester),
            'name': group['name'],
            'appl_start': group['application_start'],
            'appl_end': group['application_end'],
            'dereg_end': group['deregistration_end'],
        } for group in groups.values()]

        fields = {
            'course_nr': 'nr',
            'semester': 'sem',
            'group_name': 'name',
            'application_start': 'appl_start',
            'application_end': 'appl_end',
            'deregistration_end': 'dereg_end',
        }
        types = {
            'application_start': 'timestamptz',
            'application_end': 'timestamptz',
            'deregistration_end': 'timestamptz',
        }
        tucal.db.upsert_values('tiss.group', rows, fields, ('course_nr', 'semester', 'group_name'), types=types)

        for group in groups.values():
            data = {
                'nr': course.nr,
                'mnr': mnr,
                'sem': str(course.semester),
                'name': group['name'],
            }
            if group['enrolled']:
                cur.execute("""
                    INSERT INTO tiss.group_user (course_nr, semester, group_name, mnr)
                    VALUES (%(nr)s, %(sem)s, %(name)s, %(mnr)s)
                    ON CONFLICT ON CONSTRAINT pk_group_user DO NOTHING""", data)

            tucal.db.tiss.upsert_group_events(group['events'], group, course=course, access_time=now, mnr=int(mnr))

    for course, events in course_due_events.items():
        cur.execute("SELECT * FROM tucal.get_group(%s, %s, 'LVA')", (course.nr, str(course.semester)))
        group_nr = cur.fetch_all()[0][0]
        rows = [{
            'source': 'tiss-extra',
            'id': e['id'],
            'start': e['start'],
            'end': e['end'],
            'group': group_nr,
            'data': json.dumps({
                'tiss_extra': {
                    'name': e['name'],
                    'url': e['url'],
                },
            }),
        } for e in events]
        fields = {
            'source': 'source',
            'event_id': 'id',
            'start_ts': 'start',
            'end_ts': 'end',
            'group_nr': 'group',
            'data': 'data',
        }
        pks = tucal.db.upsert_values('tucal.external_event', rows, fields, ('source', 'event_id'), {'data': 'jsonb'})
        cur.execute(f"""
            DELETE FROM tucal.external_event
            WHERE source = 'tiss-extra' AND
                  event_id LIKE '{course.nr}-{course.semester}-%%' AND
                  event_id != ALL(%s)""", ([pk[1] for pk in pks],))

    tucal.db.commit()

    if not keep_tiss_cal_settings:
        tiss.update_calendar_settings()

    data = tiss.get_personal_schedule()
    for evt in data['events']:
        tucal.db.tiss.upsert_event(evt, now, mnr=int(mnr))

    tucal.db.commit()
    job.end(TISS_VAL_2)
    job.end(0)

    job.begin('sync tuwel', 3)
    job.begin('init tuwel')
    tuwel = tuwien.tuwel.Session(sso)
    tuwel.sso_login()

    tuwel_cal_token = tuwel.calendar_token
    user_id = tuwel.user_id
    courses = tuwel.courses

    job.end(TUWEL_INIT_VAL)
    job.begin('sync tuwel user groups', len(courses))

    groups = {}
    val = TUWEL_GROUP_VAL // len(courses) if len(courses) != 0 else 0
    for c in courses.values():
        job.begin(f'sync tuwel user groups course "{c.name[:30]}"')
        groups[c.id] = tuwel.get_course_user_groups(c.id)
        job.end(val)

    data = {
        'mnr': mnr,
        'id': user_id,
        'token': tuwel_cal_token
    }
    cur.execute("""
        INSERT INTO tuwel.user (user_id, mnr, auth_token) VALUES (%(id)s, %(mnr)s, %(token)s)
        ON CONFLICT ON CONSTRAINT pk_user DO UPDATE
        SET mnr = %(mnr)s, auth_token = %(token)s""", data)

    cur.execute("DELETE FROM tuwel.course_user WHERE user_id = %s", (user_id,))
    for c in courses.values():
        data = {
            'cid': c.id,
            'cnr': c.nr,
            'sem': str(c.semester),
            'name': c.name,
            'suffix': c.suffix,
            'short': c.short,
        }
        cur.execute("""
            INSERT INTO tuwel.course (course_id, course_nr, semester, name, suffix, short)
            VALUES (%(cid)s, %(cnr)s, %(sem)s, %(name)s, %(suffix)s, %(short)s)
            ON CONFLICT ON CONSTRAINT pk_course DO UPDATE
            SET course_nr = %(cnr)s, semester = %(sem)s, name = %(sem)s, suffix = %(suffix)s,
                short = %(short)s""", data)

        cur.execute("""
            INSERT INTO tuwel.course_user (course_id, user_id) VALUES (%s, %s)
            ON CONFLICT DO NOTHING""", (c.id, user_id))

        for group_id, group_name in groups[c.id]:
            if group_name.startswith('Gruppe ') or group_name.startswith('Kohorte '):
                name_normal = group_name
            else:
                name_normal = 'Gruppe ' + group_name
            data = {
                'name': group_name,
                'gid': group_id,
                'cid': c.id,
                'uid': user_id,
                'norm': name_normal,
            }
            cur.execute("""
                INSERT INTO tuwel.group (group_id, course_id, name, name_normalized)
                VALUES (%(gid)s, %(cid)s, %(name)s, %(norm)s)
                ON CONFLICT ON CONSTRAINT pk_group DO UPDATE
                SET course_id = %(cid)s, name = %(name)s, name_normalized = %(norm)s""", data)
            cur.execute("""
                INSERT INTO tuwel.group_user (group_id, user_id)
                VALUES (%(gid)s, %(uid)s)
                ON CONFLICT DO NOTHING""", data)

    tucal.db.commit()
    job.end(TUWEL_GROUP_VAL - val * len(courses))

    job.begin('sync tuwel calendar months', TUWEL_MONTHS)
    acc = tucal.now()
    mon_year = acc.year * 12 + acc.month - 1
    months = [((mon_year + i) // 12, (mon_year + i) % 12 + 1) for i in range(-TUWEL_MONTHS_PRE, TUWEL_MONTHS_POST - 1)]

    events = []
    for year, month in months:
        job.begin(f'sync tuwel calendar month {month}/{year}')
        r = tuwel.ajax('core_calendar_get_calendar_monthly_view', year=year, month=month)
        events += [
            evt
            for week in r['data']['weeks']
            for day in week['days']
            for evt in day['events']
        ]
        job.end(TUWEL_MONTH_VAL)
    for evt in events:
        if 'course' in evt:
            evt['course'].pop('courseimage', None)
    job.end(0)

    cur.execute("""
        DELETE FROM tuwel.event_user
        WHERE user_id = (SELECT user_id FROM tuwel.user WHERE mnr = %s) AND
              event_id = ANY(SELECT event_id FROM tuwel.event WHERE start_ts >= now())""", (mnr,))
    for evt in events:
        tucal.db.tuwel.upsert_event(evt, acc, user_id)

    tucal.db.commit()
    job.end(0)

    job.begin('sync plugin calendars')
    cur.execute("""
        SELECT course_nr FROM tucal.group_member m
        JOIN tucal.group_link g ON g.group_nr = m.group_nr
        JOIN tucal.account a ON a.account_nr = m.account_nr
        WHERE a.mnr = %s""", (mnr,))
    rows = cur.fetch_all()
    courses = [r[0] for r in rows]

    for course, p in tucal.plugins.plugins():
        if course not in courses:
            continue
        p.sync_auth(sso)
    job.end(SYNC_PLUGIN_VAL)

    job.exec(SYNC_CAL_VAL, sync_cal, mnr=int(mnr))

    cur.execute("UPDATE tucal.account SET sync_ts = now() WHERE mnr = %s", (mnr,))
    tucal.db.commit()
    cur.close()
    job.end(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mnr', '-m', required=True, type=int,
                        help='Matriculation number')
    parser.add_argument('--keep-calendar-settings', '-k', action='store_true', default=False,
                        help='Do not alter any TISS calendar settings')
    mx_group = parser.add_mutually_exclusive_group()
    mx_group.add_argument('--store', '-s', action='store_true', default=False,
                          help='Store provided password (and 2fa generator) in database')
    mx_group.add_argument('--database', '-d', action='store_true', default=False,
                          help='Fetch password (and 2fa token) from database')
    args = parser.parse_args()

    sync_user(args.mnr, use_db=args.database, store_db=args.store, keep_tiss_cal_settings=args.keep_calendar_settings)
