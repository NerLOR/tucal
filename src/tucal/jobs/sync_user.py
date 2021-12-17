
import datetime
import argparse
import base64
import random
import time
import hmac
import struct

from tucal import Job
import tucal.plugins
import tuwien.tuwel
import tuwien.tiss
import tuwien.sso
import tucal.db
import tucal.db.tiss
import tucal.db.tuwel


TUWEL_INIT_VAL = 1
TUWEL_MONTHS = 12
TUWEL_MONTH_VAL = 1
TISS_VAL = 10
SYNC_CAL_VAL = 5
SYNC_PLUGIN_VAL = 5


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mnr', '-m', required=True, type=int,
                        help='Matriculation number')
    parser.add_argument('--keep-calendar-settings', '-k', action='store_true', default=False,
                        help='Do not alter any TISS calendar settings')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--store', '-s', action='store_true', default=False,
                       help='Store provided password (and 2fa generator) in database')
    group.add_argument('--database', '-d', action='store_true', default=False,
                       help='Fetch password (and 2fa token) from database')
    args = parser.parse_args()

    cur = tucal.db.cursor()

    now = tucal.now()
    val = TUWEL_MONTHS * TUWEL_MONTH_VAL + TUWEL_INIT_VAL + TISS_VAL + SYNC_CAL_VAL + SYNC_PLUGIN_VAL
    job = Job('sync user', 4, val, estimate=20)

    mnr = f'{args.mnr:08}'
    pwd = None
    tfa_token = None
    tfa_gen = None
    if not args.database:
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

    job.begin('sync tiss')
    tiss = tuwien.tiss.Session(sso)

    try:
        tiss.sso_login()
    except tucal.InvalidCredentialsError as e:
        if args.database:
            cur.execute("""
                DELETE FROM tucal.sso_credential
                WHERE account_nr = (SELECT account_nr FROM tucal.account WHERE mnr = %s)""", (mnr,))
            tucal.db.commit()
        cur.close()
        raise e

    cur.execute("UPDATE tucal.account SET verified = TRUE, sync_ts = now() WHERE mnr = %s", (mnr,))
    if args.store:
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
            ON CONFLICT ON CONSTRAINT pk_sso_credential DO
            UPDATE SET key = %(key)s, pwd = %(pwd)s, tfa_gen = %(tfa_gen)s""", data)

    tiss_cal_token = tiss.calendar_token

    data = {
        'mnr': mnr,
        'token': tiss_cal_token,
    }
    cur.execute("""
        INSERT INTO tiss.user (mnr, auth_token) VALUES (%(mnr)s, %(token)s)
        ON CONFLICT ON CONSTRAINT pk_user DO UPDATE SET auth_token = %(token)s""", data)

    favorites = tiss.favorites
    for course in tiss.favorites:
        groups = tiss.get_groups(course)
        # TODO wait for data, then db

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
    for course in tiss.favorites:
        cur.execute("INSERT INTO tiss.course_user (course_nr, semester, mnr) VALUES (%s, %s, %s)",
                    (course.nr, str(course.semester), mnr))
        groups = tiss.get_groups(course)
        for group in groups.values():
            data = {
                'nr': course.nr,
                'sem': str(course.semester),
                'mnr': mnr,
                'name': group['name'],
                'appl_start': group['application_start'],
                'appl_end': group['application_end'],
                'dereg_end': group['deregistration_end'],
            }
            cur.execute("""
                INSERT INTO tiss.group (course_nr, semester, group_name,
                    application_start, application_end, deregistration_end)
                VALUES (%(nr)s, %(sem)s, %(name)s, %(appl_start)s, %(appl_end)s, %(dereg_end)s)
                ON CONFLICT ON CONSTRAINT pk_group DO NOTHING""", data)

            if group['enrolled']:
                cur.execute("""
                    INSERT INTO tiss.group_user (course_nr, semester, group_name, mnr)
                    VALUES (%(nr)s, %(sem)s, %(name)s, %(mnr)s)
                    ON CONFLICT ON CONSTRAINT pk_group_user DO NOTHING""", data)

            for event in group['events']:
                tucal.db.tiss.insert_group_event(event, course=course, access_time=now, mnr=int(mnr))

    if not args.keep_calendar_settings:
        tiss.update_calendar_settings()

    data = tiss.get_personal_schedule()
    for evt in data['events']:
        tucal.db.tiss.insert_event(evt, now, mnr=int(mnr))

    job.end(TISS_VAL)

    job.begin('sync tuwel', 2)
    job.begin('init tuwel')
    tuwel = tuwien.tuwel.Session(sso)
    tuwel.sso_login()

    tuwel_cal_token = tuwel.calendar_token
    user_id = tuwel.user_id
    courses = tuwel.courses

    data = {
        'mnr': mnr,
        'id': user_id,
        'token': tuwel_cal_token
    }
    cur.execute("""
        INSERT INTO tuwel.user (user_id, mnr, auth_token) VALUES (%(id)s, %(mnr)s, %(token)s)
        ON CONFLICT ON CONSTRAINT pk_user DO UPDATE SET mnr = %(mnr)s, auth_token = %(token)s""", data)

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
            ON CONFLICT ON CONSTRAINT pk_course
            DO UPDATE SET course_nr = %(cnr)s, semester = %(sem)s, name = %(sem)s, suffix = %(suffix)s,
                short = %(short)s""", data)

        cur.execute("""
            INSERT INTO tuwel.course_user (course_id, user_id) VALUES (%s, %s)
            ON CONFLICT DO NOTHING""", (c.id, user_id))
    job.end(TUWEL_INIT_VAL)

    job.begin('sync tuwel calendar months', TUWEL_MONTHS)
    acc = tucal.now()
    months = [(acc.year + (acc.month - i - 1) // 12, (acc.month - i + 11) % 12 + 1) for i in range(0, TUWEL_MONTHS)]

    events = []
    for year, month in months[::-1]:
        job.begin(f'sync tuwel calendar month {month}/{year}')
        r = tuwel.ajax('core_calendar_get_calendar_monthly_view', year=year, month=month)
        events += [
            evt
            for week in r['data']['weeks']
            for day in week['days']
            for evt in day['events']
        ]
        job.end(TUWEL_MONTH_VAL)
    job.end(0)

    cur.execute("""
        DELETE FROM tuwel.event_user
        WHERE user_id = (SELECT user_id FROM tuwel.user WHERE mnr = %s) AND
            event_id IN (SELECT event_id FROM tuwel.event WHERE start_ts >= current_date)""", (mnr,))
    for evt in events:
        tucal.db.tuwel.insert_event(evt, acc, user_id)
    job.end(0)

    tucal.db.commit()

    job.begin('sync plugin calendars')
    cur.execute("""
        SELECT course_nr FROM tucal.group_member m
        JOIN tucal.group g ON g.group_nr = m.group_nr
        JOIN tucal.account a ON a.account_nr = m.account_nr
        WHERE a.mnr = %s""", (mnr,))
    courses = [r[0] for r in cur]

    for course, p in tucal.plugins.plugins():
        if course not in courses:
            continue
        p.sync_auth(sso)
    job.end(SYNC_PLUGIN_VAL)

    job.begin('sync ical calendars')
    for cal_job, fin in tucal.schedule_job('sync-cal', f'{mnr}'):
        pass
    job.end(SYNC_CAL_VAL)

    cur.close()
    job.end(0)
