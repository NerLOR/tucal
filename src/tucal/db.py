
import typing
import psycopg2

DB_CONN: typing.Optional[psycopg2._psycopg.connection] = None

DB_HOST = 'data.necronda.net'
DB_NAME = 'tucal'
DB_USER = 'necronda'
DB_PASS = 'Password123'


def connect() -> psycopg2._psycopg.connection:
    global DB_CONN
    DB_CONN = psycopg2.connect(f'host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS}')
    return DB_CONN


def cursor() -> psycopg2._psycopg.cursor:
    if DB_CONN is None:
        connect()
    return DB_CONN.cursor()


def commit() -> bool:
    if DB_CONN is None:
        return False
    DB_CONN.commit()
    return True
