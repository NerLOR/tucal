
import time

import tucal.db


if __name__ == '__main__':
    cur = tucal.db.cursor()
    while True:
        cur.execute("""
            SELECT * FROM tucal.external_event""")
        rows = cur.fetchall()
        time.sleep(1)
