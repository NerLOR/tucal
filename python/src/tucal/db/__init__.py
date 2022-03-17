
from __future__ import annotations
from typing import Union, List, Tuple, Dict, Optional, Any, Iterable
import re
import psycopg2
import psycopg2.extras

import tucal


DB_CONN: Optional[Connection] = None
DB_TZ = 'Europe/Vienna'

_VALS = Union[List[Any], Tuple, Dict[str, Any]]


config = tucal.get_config()
DB_CONFIG = {
    'host': config['database']['host'],
    'port': int(config['database']['port']),
    'dbname': config['database']['name'],
    'user': config['database']['user'],
    'password': config['database']['password']
}


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
            pos_start = sql.find('VALUES')
            if pos_start != -1:
                pos_end = pos_start
                i, mx = 0, 0
                while (i != 0 or mx == 0) and pos_end < len(sql):
                    c = sql[pos_end]
                    if c == '(':
                        i += 1
                        mx += 1
                    elif c == ')':
                        i -= 1
                    pos_end += 1
                template = sql[pos_start + 6:pos_end]
                sql = sql[:pos_start] + 'VALUES %s' + sql[pos_end:]
        return psycopg2.extras.execute_values(self.cursor, sql, data, template=template)

    def fetch_one(self) -> Tuple:
        return self.cursor.fetchone()

    def fetch_all(self) -> List[Tuple]:
        return self.cursor.fetchall()

    def lock(self, tables: Iterable[str], mode: str = 'ROW EXCLUSIVE') -> bool:
        return self.cursor.execute(f"LOCK TABLE {', '.join(tables)} IN {mode} MODE")

    def __del__(self):
        del self.cursor


class Connection(psycopg2._psycopg.connection):
    pass


def connect() -> Connection:
    global DB_CONN
    DB_CONN = psycopg2.connect(**DB_CONFIG)
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


def rollback() -> bool:
    if DB_CONN is None:
        return False
    DB_CONN.rollback()
    return True


def upsert_values(table: str, data: List[Dict[str, Any]], fields: Dict[str, str], pk: Tuple,
                  types: Dict[str, str] = None) -> List[Tuple]:
    types = types or {}
    cur = cursor()
    cur.execute(f"SELECT {', '.join(pk)} FROM {table}")
    pks = cur.fetch_all()
    rows_insert = []
    rows_update = []
    upserted = []

    for row in data:
        row_id = tuple([row[fields[d]] for d in pk])
        if row_id in pks:
            rows_update.append(row)
            upserted.append(row_id)
        else:
            rows_insert.append(row)
            pks.append(row_id)

    template = '(' + ', '.join([f'%({k})s' for k in fields.values()]) + ')'

    if len(rows_insert) > 0:
        sql = f"INSERT INTO {table} ({', '.join(fields.keys())}) VALUES %s RETURNING {', '.join(pk)}"
        cur.execute_values(sql, rows_insert, template=template)
        inserted = cur.fetch_all()
        upserted += inserted

    if len(rows_update) > 0:
        var = ', '.join([
            a + ' = ' + 'd.' + a + (('::' + types[a]) if a in types else '')
            for a in fields.keys() - set(pk)
        ])
        sql = f"""UPDATE {table} t SET {var}
                  FROM (VALUES %s) AS d ({', '.join(fields.keys())})
                  WHERE ({','.join(['t.' + k for k in pk])}) = ({', '.join(['d.' + k for k in pk])})"""
        cur.execute_values(sql, rows_update, template=template)

    return upserted
