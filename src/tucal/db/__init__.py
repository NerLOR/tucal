
from __future__ import annotations
import typing
import psycopg2

DB_CONN: typing.Optional[Connection] = None

DB_HOST = 'data.necronda.net'
DB_NAME = 'tucal'
DB_USER = 'necronda'
DB_PASS = 'Password123'
DB_TZ = 'Europe/Vienna'


class Cursor(psycopg2._psycopg.cursor):
    pass


class Connection(psycopg2._psycopg.connection):
    pass


def connect() -> Connection:
    global DB_CONN
    DB_CONN = psycopg2.connect(f'host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS}')
    return DB_CONN


def cursor() -> Cursor:
    if DB_CONN is None:
        connect()
    cur = DB_CONN.cursor()
    cur.execute(f"SET TIME ZONE '{DB_TZ}'")
    return cur


def commit() -> bool:
    if DB_CONN is None:
        return False
    DB_CONN.commit()
    return True
