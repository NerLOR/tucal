
from socketserver import UnixStreamServer, StreamRequestHandler, ThreadingMixIn
import subprocess
import os
import time
import json
import atexit
import base64
import re

import tucal
import tucal.db


CHILDREN = {}


def on_exit():
    print('cleaning up child processes', flush=True)
    cur = tucal.db.cursor()
    for pid, data in CHILDREN.items():
        proc = data['proc']
        job_nr = data['job_nr']
        print(f'killing {proc.pid}...', flush=True)
        cur.execute("UPDATE tucal.job SET status = 'aborted', pid = NULL WHERE job_nr = %s", (job_nr,))
        proc.terminate()
    tucal.db.commit()
    print('cleanup complete', flush=True)


class Handler(StreamRequestHandler):
    def handle(self):
        job = self.rfile.readline()
        if not job:
            self.wfile.write(b'error: no input\n')
            return
        job = re.sub(r'\s+', ' ', job.decode('utf8').strip()).split(' ')
        job_name, job = job[0], job[1:]
        cur = tucal.db.cursor()

        cmd = ['python3', '-m']
        stdin = ''
        mnr = None
        if job_name == 'sync-user':
            # sync-user [store] [keep] <mnr> [<pwd-b64> [<2fa-token> | <2fa-generator-b64>]]
            cmd += ['tucal.jobs.sync_user']
            if len(job) > 0 and job[0] == 'store':
                job.pop(0)
                cmd += ['-s']
            if len(job) > 0 and job[0] == 'keep':
                job.pop(0)
                cmd += ['-k']
            if len(job) == 0:
                self.wfile.write(b'error: job sync-user requires at least one argument <mnr>\n')
                return
            mnr = int(job[0])
            cmd += ['-m', str(mnr)]
            if len(job) > 1:
                stdin += base64.b64decode(job[1]).decode('utf8') + '\n'
            else:
                cmd += ['-d']
            if len(job) > 2:
                stdin += job[2] + '\n'
        elif job_name == 'sync-cal':
            # sync-cal [<mnr>]
            cmd += ['tucal.jobs.sync_cal']
            if len(job) > 0:
                cmd += ['-m', job[0]]
        elif job_name == 'sync-users':
            # sync-users
            cmd += ['tucal.jobs.sync_users']
            if len(job) > 0:
                self.wfile.write(b'error: job sync-users has no additional arguments\n')
                return
        else:
            self.wfile.write(b'error: unknown job type\n')
            return

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        pid = proc.pid
        CHILDREN[pid] = {'proc': proc}
        proc.stdin.write(stdin.encode('utf8'))
        proc.stdin.close()

        data = {
            'name': f'',
            'pid': pid,
            'mnr': mnr,
            'status': 'running',
            'data': '{}'
        }
        cur.execute("""
            INSERT INTO tucal.job (name, pid, mnr, status)
            VALUES (%(name)s, %(pid)s, %(mnr)s, %(status)s)
            RETURNING job_nr, job_id""", data)
        tucal.db.commit()
        job_nr, job_id = cur.fetch_all()[0]

        CHILDREN[pid]['job_nr'] = job_nr

        print(f'[{job_nr:8}] {job_name} - PID {pid} - {" ".join(cmd)}', flush=True)
        self.wfile.write(f'{job_nr} {job_id} {pid}\n'.encode('utf8'))

        reader = tucal.JobStatus()
        data = {
            'nr': job_nr,
            'status': 'running',
            'name': None,
            'time': reader.time,
            'start': reader.start.isoformat() if reader.start else None,
            'data': reader.json(),
            'err': None,
        }

        while proc.returncode is None:
            line = proc.stdout.readline().decode('utf8')
            if len(line) > 0:
                try:
                    self.wfile.write(b'stdout:' + line.encode('utf8'))
                except BrokenPipeError:
                    pass
            if not reader.line(line):
                proc.poll()
                time.sleep(0.125)
                continue

            data['time'] = reader.time
            data['start'] = reader.start.isoformat() if reader.start else None
            data['name'] = reader.steps[0]['name'] if len(reader.steps) > 0 else None
            data['data'] = reader.json()
            cur.execute("""
                UPDATE tucal.job
                SET data = %(data)s, status = %(status)s, start_ts = %(start)s, time = %(time)s, name = %(name)s
                WHERE job_nr = %(nr)s""", data)
            tucal.db.commit()

        proc.stdout.read()
        err = proc.stderr.read().decode('utf8')
        if len(err) > 0:
            print('\n'.join([f'[{job_nr:8}] {line}' for line in err.rstrip().splitlines()]), flush=True)
            try:
                self.wfile.write(b'\n'.join(
                    [b'stderr:' + line.encode('utf8') for line in err.rstrip().splitlines()]
                ) + b'\n')
            except BrokenPipeError:
                pass

        data['data'] = reader.json()

        if len(err) > 0:
            d = json.loads(data['data'])
            d['error'] = err
            data['data'] = json.dumps(d)

        data['status'] = 'success' if proc.returncode == 0 else 'error'
        try:
            self.wfile.write(f'status:{proc.returncode}\n'.encode('utf8'))
        except BrokenPipeError:
            pass

        cur.execute("""
            UPDATE tucal.job
            SET data = %(data)s, status = %(status)s, pid = NULL
            WHERE job_nr = %(nr)s""", data)
        tucal.db.commit()

        proc.stdout.close()
        proc.stderr.close()
        proc.terminate()

        print(f'[{job_nr:8}] terminated', flush=True)
        del CHILDREN[pid]
        self.wfile.close()
        self.rfile.close()


class ThreadedUnixStreamServer(ThreadingMixIn, UnixStreamServer):
    pass


if __name__ == '__main__':
    atexit.register(on_exit)
    try:
        os.unlink('/var/tucal/scheduler.sock')
    except FileNotFoundError:
        pass
    with ThreadedUnixStreamServer('/var/tucal/scheduler.sock', Handler) as server:
        server.serve_forever()
