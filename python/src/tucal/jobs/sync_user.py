
from typing import List, Dict, Any, Tuple
import argparse
import random
import base64
import time
import struct
import hmac
import json
import datetime

from tucal import Job
from tucal.jobs.sync_cal import SyncCalendar
import tucal.db
import tucal.db.tiss
import tucal.db.tuwel
import tucal.plugins
import tuwien.sso
import tuwien.tiss
import tuwien.tuwel


FETCH_TISS_COURSES_VAL = 6 * 30
TISS_REQ_VAL = 10
FETCH_TISS_VAL = 4 * TISS_REQ_VAL + FETCH_TISS_COURSES_VAL

TUWEL_MONTHS_PRE = 12
TUWEL_MONTHS_POST = 6
TUWEL_MONTHS = TUWEL_MONTHS_PRE + TUWEL_MONTHS_POST
TUWEL_GROUP_VAL = 100
TUWEL_MONTH_VAL = 10
TUWEL_INIT_VAL = 10
FETCH_TUWEL_VAL = TUWEL_INIT_VAL + TUWEL_GROUP_VAL + TUWEL_MONTH_VAL * TUWEL_MONTHS


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


class SyncUserTiss(tucal.Sync):
    job: Job
    mnr: str
    mnr_int: int

    access_time: datetime.datetime = None
    cal_token: str = None
    favorites: List[tuwien.tiss.Course] = None
    course_events: Dict[tuwien.tiss.Course, List] = None
    course_groups: Dict[tuwien.tiss.Course, Dict] = None
    course_extra_events: Dict[tuwien.tiss.Course, List] = None
    personal_schedule: Dict[str, Any] = None

    def __init__(self, session: tuwien.sso.Session, job: Job, mnr: int):
        super().__init__(session)
        self.job = job
        self.mnr = f'{mnr:08}'
        self.mnr_int = int(mnr)

    def fetch(self, keep_tiss_cal_settings: bool = True):
        self.job.init('fetch tiss user data', 5, FETCH_TISS_VAL)

        self.job.begin('login tiss')
        tiss = tuwien.tiss.Session(self.session)
        tiss.sso_login()
        self.job.end(TISS_REQ_VAL)

        self.job.begin('sync tiss user favorites')
        self.access_time = tucal.now()
        self.favorites = tiss.favorites
        self.job.end(TISS_REQ_VAL)

        val = FETCH_TISS_COURSES_VAL // len(self.favorites) if len(self.favorites) > 0 else 0
        self.job.begin('sync tiss courses', len(self.favorites))
        self.course_events = {}
        self.course_groups = {}
        self.course_extra_events = {}
        for course in self.favorites:
            self.job.begin(f'sync tiss course "{course.name_de[:30]}"')
            self.course_events[course] = tiss.get_course_events(course)
            self.course_groups[course] = tiss.get_groups(course)
            self.course_extra_events[course] = tiss.get_course_extra_events(course)
            self.job.end(val)
        self.job.end(FETCH_TISS_COURSES_VAL - len(self.favorites) * val)

        self.job.begin('fetch tiss calendar token')
        self.cal_token = tiss.calendar_token
        if not keep_tiss_cal_settings:
            tiss.update_calendar_settings()
        self.job.end(TISS_REQ_VAL)

        self.job.begin('sync tiss personal schedule')
        self.personal_schedule = tiss.get_personal_schedule()
        self.job.end(TISS_REQ_VAL)

        self.job.end(0)

    def store(self, cur: tucal.db.Cursor):
        self.job.init('store tiss user data', 0, 1)

        cur.execute("""
                INSERT INTO tiss.user (mnr, auth_token) VALUES (%(mnr)s, %(token)s)
                ON CONFLICT ON CONSTRAINT pk_user DO UPDATE
                SET auth_token = %(token)s""", {
            'mnr': self.mnr_int,
            'token': self.cal_token,
        })

        cur.execute("DELETE FROM tiss.course_user WHERE mnr = %s", (self.mnr_int,))
        cur.execute("""
                DELETE FROM tiss.group_user u
                WHERE u.mnr = %s AND
                (SELECT g.deregistration_end > now() FROM tiss.group g
                    WHERE (g.course_nr, g.semester, g.group_name) = (u.course_nr, u.semester, u.group_name))""", (
            self.mnr_int,
        ))
        cur.execute("""
                DELETE FROM tiss.exam_user u
                WHERE mnr = %s AND
                (SELECT e.deregistration_end > now() FROM tiss.exam e
                    WHERE (e.course_nr, e.semester, e.exam_name) = (u.course_nr, u.semester, u.exam_name))""", (
            self.mnr_int,
        ))

        cur.execute_values("INSERT INTO tiss.course_user (course_nr, semester, mnr) VALUES (%s, %s, %s)",
                           [(course.nr, str(course.semester), self.mnr_int) for course in self.favorites])

        for course, events in self.course_events.items():
            tucal.db.tiss.upsert_course_events(events, course, access_time=self.access_time, mnr=self.mnr_int)

        for course, groups in self.course_groups.items():
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
                if group['enrolled']:
                    cur.execute("""
                            INSERT INTO tiss.group_user (course_nr, semester, group_name, mnr)
                            VALUES (%(nr)s, %(sem)s, %(name)s, %(mnr)s)
                            ON CONFLICT ON CONSTRAINT pk_group_user DO NOTHING""", {
                        'nr': course.nr,
                        'mnr': self.mnr_int,
                        'sem': str(course.semester),
                        'name': group['name'],
                    })

                tucal.db.tiss.upsert_group_events(group['events'], group, course=course,
                                                  access_time=self.access_time, mnr=self.mnr_int)

        for course, events in self.course_extra_events.items():
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
                        'exam': e['exam'] if 'exam' in e else None,
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
            pks = tucal.db.upsert_values('tucal.external_event', rows, fields, ('source', 'event_id'),
                                         {'data': 'jsonb'})
            cur.execute(f"""
                DELETE FROM tucal.external_event
                WHERE source = 'tiss-extra' AND
                      event_id LIKE '{course.nr}-{course.semester}-%%' AND
                      event_id != ALL(%s)""", ([pk[1] for pk in pks],))

        tucal.db.tiss.upsert_events(self.personal_schedule['events'], self.access_time, mnr=self.mnr_int)

        self.job.end(1)


class SyncUserTuwel(tucal.Sync):
    job: Job
    mnr: str
    mnr_int: int

    access_time: datetime.datetime = None
    user_id: int = None
    cal_token: str = None
    courses: Dict[int, tuwien.tuwel.Course] = None
    groups: Dict[int, List] = None
    events: List[Dict[str, Any]] = None

    def __init__(self, session: tuwien.sso.Session, job: Job, mnr: int):
        super().__init__(session)
        self.job = job
        self.mnr = f'{mnr:08}'
        self.mnr_int = int(mnr)

    def fetch(self):
        self.job.init('sync tuwel', 3, FETCH_TUWEL_VAL)

        self.job.begin('init tuwel')
        tuwel = tuwien.tuwel.Session(self.session)
        tuwel.sso_login()

        self.cal_token = tuwel.calendar_token
        self.user_id = tuwel.user_id
        self.courses = tuwel.courses
        self.job.end(TUWEL_INIT_VAL)

        self.job.begin('sync tuwel user groups', len(self.courses))

        self.groups = {}
        val = TUWEL_GROUP_VAL // len(self.courses) if len(self.courses) != 0 else 0
        for c in self.courses.values():
            self.job.begin(f'sync tuwel user groups course "{c.name[:30]}"')
            self.groups[c.id] = tuwel.get_course_user_groups(c.id)
            self.job.end(val)

        self.job.end(TUWEL_GROUP_VAL - val * len(self.courses))

        self.job.begin('sync tuwel calendar months', TUWEL_MONTHS)
        self.access_time = tucal.now()
        mon_year = self.access_time.year * 12 + self.access_time.month - 1
        months = [
            ((mon_year + i) // 12, (mon_year + i) % 12 + 1)
            for i in range(-TUWEL_MONTHS_PRE, TUWEL_MONTHS_POST - 1)
        ]

        self.events = []
        for year, month in months:
            self.job.begin(f'sync tuwel calendar month {month}/{year}')
            r = tuwel.ajax('core_calendar_get_calendar_monthly_view', year=year, month=month)
            self.events += [
                evt
                for week in r['data']['weeks']
                for day in week['days']
                for evt in day['events']
            ]
            self.job.end(TUWEL_MONTH_VAL)
        for evt in self.events:
            if 'course' in evt:
                evt['course'].pop('courseimage', None)
        self.job.end(0)

        self.job.end(0)

    def store(self, cur: tucal.db.Cursor):
        self.job.init('store tuwel data', 0, 1)

        cur.execute("""
                INSERT INTO tuwel.user (user_id, mnr, auth_token) VALUES (%(id)s, %(mnr)s, %(token)s)
                ON CONFLICT ON CONSTRAINT pk_user DO UPDATE
                SET mnr = %(mnr)s, auth_token = %(token)s""", {
            'mnr': self.mnr,
            'id': self.user_id,
            'token': self.cal_token
        })

        cur.execute("SELECT course_nr, semester FROM tiss.course")
        courses = [(str(cnr), str(sem)) for cnr, sem in cur.fetch_all()]

        removed_courses = []
        cur.execute("DELETE FROM tuwel.course_user WHERE user_id = %s", (self.user_id,))
        for c in self.courses.values():
            if c.nr is not None and c.semester is not None and (c.nr, str(c.semester)) not in courses:
                print(f'Warning: TUWEL course {c.nr}-{c.semester} not in database (id {c.id})')
                removed_courses.append(c.id)
                continue

            data = {
                'cid': c.id,
                'cnr': c.nr,
                'sem': str(c.semester) if c.semester else None,
                'name': c.name,
                'suffix': c.suffix,
                'short': c.short,
            }
            cur.execute("""
                INSERT INTO tuwel.course (course_id, course_nr, semester, name, suffix, short)
                VALUES (%(cid)s, %(cnr)s, %(sem)s, %(name)s, %(suffix)s, %(short)s)
                ON CONFLICT ON CONSTRAINT pk_course DO UPDATE
                SET course_nr = %(cnr)s, semester = %(sem)s, name = %(name)s, suffix = %(suffix)s,
                    short = %(short)s""", data)

            cur.execute("""
                INSERT INTO tuwel.course_user (course_id, user_id) VALUES (%s, %s)
                ON CONFLICT DO NOTHING""", (c.id, self.user_id))

            if c.nr is None or c.semester is None:
                continue

            for group_id, group_name in self.groups[c.id]:
                if group_name.startswith('Gruppe ') or group_name.startswith('Kohorte '):
                    name_normal = group_name
                else:
                    name_normal = 'Gruppe ' + group_name

                data = {
                    'name': group_name,
                    'gid': group_id,
                    'cid': c.id,
                    'uid': self.user_id,
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

        # remove user events (with no course id)
        self.events = [e for e in self.events if 'course' in e]

        events = [e for e in self.events if e['course']['id'] not in removed_courses]
        num_skipped_events = len([e for e in self.events if e['course']['id'] in removed_courses])
        if num_skipped_events > 0:
            print(f'Warning: had to skip {num_skipped_events} event(s)')

        cur.execute("""
            DELETE FROM tuwel.event_user
            WHERE user_id = (SELECT user_id FROM tuwel.user WHERE mnr = %s) AND
                  event_id = ANY(SELECT event_id FROM tuwel.event WHERE start_ts >= now())""", (self.mnr_int,))
        tucal.db.tuwel.upsert_events(events, self.access_time, self.user_id)

        self.job.end(1)


class SyncUser(tucal.Sync):
    job: Job
    mnr: str
    mnr_int: int
    courses: List[Tuple[str, str]]
    plugins: List[tucal.Sync]
    tiss: SyncUserTiss
    tuwel: SyncUserTuwel
    cal: SyncCalendar

    def __init__(self, session: tuwien.sso.Session, mnr: int, job: Job = None):
        super().__init__(session)
        self.mnr = f'{mnr:08}'
        self.mnr_int = int(mnr)
        self.job = job or Job()
        self.tiss = SyncUserTiss(session, self.job, self.mnr_int)
        self.tuwel = SyncUserTuwel(session, self.job, self.mnr_int)
        self.cal = SyncCalendar(tuwien.sso.Session(), self.mnr_int, self.job)

    def login(self, pwd_from_db: bool = False, pwd_store_db: bool = False):
        tucal.db.rollback()
        cur = tucal.db.cursor()
        cur.execute("UPDATE tucal.account SET sync_try_ts = now() WHERE mnr = %s", (self.mnr_int,))

        tfa_token, tfa_gen = None, None
        if not pwd_from_db:
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
                SELECT key, pwd, tfa_gen
                FROM tucal.sso_credential
                WHERE account_nr = (SELECT account_nr FROM tucal.account WHERE mnr = %s)""", (self.mnr_int,))
            cred = cur.fetch_all()
            if len(cred) == 0:
                raise RuntimeError('account credentials not found in database')
            acc_key, pwd_enc, tfa_gen_enc = cred[0]
            pwd = dec(pwd_enc, acc_key).decode('utf8')
            tfa_gen = dec(tfa_gen_enc, acc_key) if tfa_gen_enc is not None else None

        try:
            if tfa_token is None and tfa_gen is not None:
                for i in range(6):
                    tfa_token = totp_gen_token(tfa_gen)
                    self.session.credentials(self.mnr, pwd, tfa_token)
                    try:
                        self.session.login()
                        break
                    except tucal.InvalidCredentialsError as e:
                        if i == 5:
                            raise e
                    time.sleep(10)
            else:
                self.session.credentials(self.mnr, pwd, tfa_token)
                self.session.login()
        except tucal.InvalidCredentialsError as e:
            if pwd_from_db:
                cur.execute("""
                    DELETE FROM tucal.sso_credential
                    WHERE account_nr = (SELECT account_nr FROM tucal.account WHERE mnr = %s)""", (self.mnr_int,))
                tucal.db.commit()
            raise e

        cur.execute("UPDATE tucal.account SET verified = TRUE WHERE mnr = %s", (self.mnr_int,))

        if pwd_store_db:
            acc_key = random.randint(10, 200)
            pwd_enc = enc(pwd.encode('utf8'), acc_key)
            tfa_gen_enc = enc(tfa_gen, acc_key) if tfa_gen is not None else None
            cur.execute("""
                    INSERT INTO tucal.sso_credential (account_nr, key, pwd, tfa_gen)
                    VALUES ((SELECT account_nr FROM tucal.account WHERE mnr = %(mnr)s), %(key)s, %(pwd)s, %(tfa_gen)s)
                    ON CONFLICT ON CONSTRAINT pk_sso_credential DO UPDATE
                    SET key = %(key)s, pwd = %(pwd)s, tfa_gen = %(tfa_gen)s""", {
                'mnr': self.mnr_int,
                'key': acc_key,
                'pwd': pwd_enc,
                'tfa_gen': tfa_gen_enc,
            })

        tucal.db.commit()

    def fetch_plugins(self):
        self.job.begin('fetch plugin calendars')
        cur = tucal.db.cursor()
        cur.execute("""
                    SELECT course_nr, semester
                    FROM tucal.group_member m
                        JOIN tucal.group_link g ON g.group_nr = m.group_nr
                        JOIN tucal.account a ON a.account_nr = m.account_nr
                    WHERE a.mnr = %s""", (self.mnr_int,))
        rows = cur.fetch_all()
        cur.close()
        tucal.db.rollback()
        self.courses = [(r[0], r[1]) for r in rows]
        self.plugins = []
        course_nrs = [c[0] for c in self.courses]
        for course, p in tucal.plugins.plugins():
            if course not in course_nrs:
                continue
            plugin_sync = p.sync_auth(self.session)
            if plugin_sync:
                try:
                    plugin_sync.fetch()
                    self.plugins.append(plugin_sync)
                except Exception as e:
                    print(f'Unable to fetch plugin {course}: {e}')
        self.job.end(1)

    def fetch(self, keep_tiss_cal_settings: bool = True):
        self.job.init('fetch user calendars', 4, 24)

        self.job.exec(11, self.tiss.fetch, False, keep_tiss_cal_settings=keep_tiss_cal_settings)
        self.job.exec(11, self.tuwel.fetch, False)
        self.job.exec(1, self.cal.fetch, False)

        self.fetch_plugins()

        self.job.end(0)

    def _delete_user_group(self, cur: tucal.db.Cursor):
        sem = str(tucal.Semester.current())

        cur.execute("DELETE FROM tiss.course_user WHERE (mnr, semester) = (%s, %s)", (self.mnr_int, sem))
        cur.execute("DELETE FROM tiss.group_user WHERE (mnr, semester) = (%s, %s)", (self.mnr_int, sem))
        cur.execute("DELETE FROM tiss.exam_user WHERE (mnr, semester) = (%s, %s)", (self.mnr_int, sem))

        cur.execute("SELECT user_id FROM tuwel.user WHERE mnr = %s", (self.mnr_int,))
        user_ids = cur.fetch_all()
        if len(user_ids) > 0:
            user_id = user_ids[0]
            cur.execute("""
                DELETE FROM tuwel.course_user
                WHERE user_id = %s AND
                      course_id = ANY(
                            SELECT course_id
                            FROM tuwel.course
                            WHERE semester = %s
                      )""", (user_id, sem))
            cur.execute("""
                DELETE FROM tuwel.group_user
                WHERE user_id = %s AND
                      group_id = ANY(
                            SELECT g.group_id
                            FROM tuwel.group g
                                JOIN tuwel.course c ON c.course_id = g.course_id
                            WHERE c.semester = %s
                      )""", (user_id, sem))

        cur.execute("""
            DELETE FROM tucal.group_member
            WHERE account_nr = (SELECT account_nr FROM tucal.account WHERE mnr = %s) AND
                  group_nr = ANY(
                        SELECT g.group_nr
                        FROM tucal.group g
                            JOIN tucal.group_link l ON l.group_nr = g.group_nr
                        WHERE l.semester = %s
                  )""", (self.mnr_int, sem))

    def store_plugins(self, cur: tucal.db.Cursor):
        self.job.begin('store plugin calendars')
        for plugin in self.plugins:
            plugin.store(cur)
        self.job.end(2)

    def store(self, cur: tucal.db.Cursor, reset_semester: bool = False):
        self.job.init('store user calendars', 4 + (1 if reset_semester else 0), 12 + (2 if reset_semester else 0))

        cur.lock(('tucal.event', 'tucal.external_event', 'tucal.group', 'tucal.group_member',
                  'tiss.event', 'tiss.course', 'tiss.group', 'tiss.exam',
                  'tiss.event_user', 'tiss.course_user', 'tiss.group_user', 'tiss.exam_user',
                  'tuwel.event', 'tuwel.course', 'tuwel.group',
                  'tuwel.event_user', 'tuwel.course_user', 'tuwel.group_user'),
                 mode='SHARE ROW EXCLUSIVE')

        if reset_semester:
            self.job.begin('reset user semester groups')
            self._delete_user_group(cur)
            self.job.end(2)

        self.job.exec(3, self.tiss.store, False, cur=cur)
        self.job.exec(3, self.tuwel.store, False, cur=cur)
        self.job.exec(3, self.cal.store, False, cur=cur)  # TUWEL courses need to be created first

        self.store_plugins(cur)

        cur.execute("UPDATE tucal.account SET sync_ts = now() WHERE mnr = %s", (self.mnr_int,))
        self.job.end(1)

    def pre_sync(self):
        self.job.init('sync user', 2, 6, estimate=70)

    def sync(self, keep_tiss_cal_settings: bool = True, reset_semester: bool = False):
        cur = tucal.db.cursor()
        self.job.exec(5, self.fetch, False, keep_tiss_cal_settings=keep_tiss_cal_settings)
        self.job.exec(1, self.store, False, cur=cur, reset_semester=reset_semester)
        cur.close()
        self.job.end(0)

    def sync_plugins(self):
        cur = tucal.db.cursor()
        sync_user.fetch_plugins()
        sync_user.store_plugins(cur)
        cur.close()
        self.job.end(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mnr', '-m', required=True, type=int,
                        help='Matriculation number')
    parser.add_argument('--keep-calendar-settings', '-k', action='store_true', default=False,
                        help='Do not alter any TISS calendar settings')
    parser.add_argument('--reset-semester', '-r', action='store_true', default=False,
                        help='Reset user groups and courses for the current semester')
    parser.add_argument('--plugins-only', '-p', action='store_true', default=False,
                        help='Do only sync plugins, nothing else. For debug purposes only!')
    mx_group = parser.add_mutually_exclusive_group()
    mx_group.add_argument('--store', '-s', action='store_true', default=False,
                          help='Store provided password (and 2fa generator) in database')
    mx_group.add_argument('--database', '-d', action='store_true', default=False,
                          help='Fetch password (and 2fa token) from database')
    args = parser.parse_args()

    sync_user = SyncUser(tuwien.sso.Session(), args.mnr)
    sync_user.pre_sync()
    sync_user.login(pwd_from_db=args.database, pwd_store_db=args.store)
    if args.plugins_only:
        sync_user.sync_plugins()
    else:
        sync_user.sync(keep_tiss_cal_settings=args.keep_calendar_settings, reset_semester=args.reset_semester)
    tucal.db.commit()
