
from __future__ import annotations
from typing import Union, List, Tuple, Dict, Optional, Any
import re
import psycopg2
import psycopg2.extras


DB_CONN: Optional[Connection] = None

DB_HOST = 'data.necronda.net'
DB_NAME = 'tucal'
DB_USER = 'necronda'
DB_PASS = 'Password123'
DB_TZ = 'Europe/Vienna'

VALUES = re.compile(r'VALUES\s+(\((\s*%(\(.*?\))?s\s*,?\s*)*\))')

_VALS = Union[List[Any], Tuple, Dict[str, Any]]


class Cursor:
    cursor: psycopg2._psycopg.cursor

    def __init__(self, cur: psycopg2._psycopg.cursor):
        self.cursor = cur

    def close(self):
        return self.cursor.close()

    def execute(self, sql: str, data: _VALS = None) -> None:
        return self.cursor.execute(sql, data)

    def execute_values(self, sql: str, data: List[_VALS], template: str = None):
        if template is None:
            vals = VALUES.findall(sql)
            if len(vals) > 0:
                sql = VALUES.sub('VALUES %s', sql)
                template = vals[0][0]
        return psycopg2.extras.execute_values(self.cursor, sql, data, template=template)

    def fetch_one(self) -> Tuple:
        return self.cursor.fetchone()

    def fetch_all(self) -> List[Tuple]:
        return self.cursor.fetchall()

    def __iter__(self) -> Tuple:
        return self.cursor.__iter__()

    def __del__(self):
        del self.cursor


class Connection(psycopg2._psycopg.connection):
    pass


def connect() -> Connection:
    global DB_CONN
    DB_CONN = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
    return DB_CONN


def cursor() -> Cursor:
    if DB_CONN is None:
        connect()
    cur = Cursor(DB_CONN.cursor())
    cur.execute(f"SET TIME ZONE '{DB_TZ}'")
    return cur


def commit() -> bool:
    if DB_CONN is None:
        return False
    DB_CONN.commit()
    return True


def upsert(table: str, data: List[Dict[str, Any]], fields: Dict[str, str], pk: Tuple):
    cur = cursor()
    cur.execute(f"SELECT {','.join(pk)} FROM {table}")
    pks = cur.fetch_all()
    rows_insert = []
    rows_update = []

    for row in data:
        row_id = tuple([row[fields[d]] for d in pk])
        if row_id in pks:
            rows_update.append(row)
        else:
            rows_insert.append(row)

    template = '(' + ', '.join([f'%({k})s' for k in fields.values()]) + ')'

    if len(rows_insert) > 0:
        sql = f"INSERT INTO {table} ({','.join(fields.keys())}) VALUES %s"
        cur.execute_values(sql, rows_insert, template=template)

    if len(rows_update) > 0:
        sql = f"""UPDATE {table} t SET {', '.join([ a + ' = ' + 'd.' + a for a in fields.keys() - set(pk)])}
                  FROM (VALUES %s) AS d ({', '.join(fields.keys())})
                  WHERE ({','.join(['t.' + k for k in pk])}) = ({', '.join(['d.' + k for k in pk])})"""
        cur.execute_values(sql, rows_update, template=template)
