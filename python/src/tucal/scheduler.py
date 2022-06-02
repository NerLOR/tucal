from socketserver import UnixStreamServer, StreamRequestHandler, ThreadingMixIn
import subprocess
import os
import time
import json
import signal
import base64
import re

import tucal
import tucal.db


CHILDREN = {}
CLEANUP_STARTED = False


def cleanup_jobs():
    cur = tucal.db.cursor()
    cur.execute("UPDATE tucal.job SET status = 'aborted', pid = NULL WHERE status = ANY('{waiting, running}')")
    cur.close()
    tucal.db.commit()


def cleanup():
    global CLEANUP_STARTED
    if CLEANUP_STARTED:
        return
    CLEANUP_STARTED = True

    print('cleaning up child processes', flush=True)
    for pid, data in CHILDREN.items():
        proc = data['proc']
        print(f'killing {proc.pid}...', flush=True)
        proc.terminate()

    time.sleep(1)

    print('cleaning up jobs', flush=True)
    cleanup_jobs()

    print('cleanup complete', flush=True)
    exit(0)


def signal_exit(signal_num: int, frame):
    cleanup()


class Handler(StreamRequestHandler):
    def handle(self):
        job = self.rfile.readline()
        if not job:
            self.wfile.write(b'error: no input\n')
            return
        job = re.sub(r'\s+', ' ', job.decode('utf8').strip()).split(' ')
        delay, job_name, job = int(job[0]), job[1], job[2:]
        cur = tucal.db.cursor()

        cmd = ['python3', '-m']
        stdin = ''
        mnr = None
        if job_name == 'sync-user':
            # sync-user [store] [keep] [reset] <mnr> [<pwd-b64> [<2fa-token> | <2fa-generator-b64>]]
            cmd += ['tucal.jobs.sync_user']
            if len(job) > 0 and job[0] == 'store':
                job.pop(0)
                cmd += ['-s']
            if len(job) > 0 and job[0] == 'keep':
                job.pop(0)
                cmd += ['-k']
            if len(job) > 0 and job[0] == 'reset':
                job.pop(0)
                cmd += ['-r']
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
        elif job_name == 'sync-plugins':
            # sync-plugins
            cmd += ['tucal.jobs.sync_plugins']
            if len(job) > 0:
                self.wfile.write(b'error:job sync-plugins has no additional arguments\n ')
                return
        else:
            self.wfile.write(b'error: unknown job type\n')
            return

        data = {
            'name': job_name.replace('_', ' '),
            'pid': None,
            'mnr': mnr,
            'status': 'waiting',
            'data': '{}',
        }
        cur.execute("""
            INSERT INTO tucal.job (name, pid, mnr, status)
            VALUES (%(name)s, %(pid)s, %(mnr)s, %(status)s)
            RETURNING job_nr, job_id""", data)
        tucal.db.commit()
        job_nr, job_id = cur.fetch_all()[0]
        data['nr'] = job_nr
        data['id'] = job_id

        self.wfile.write(f'{job_nr} {job_id}\n'.encode('utf8'))

        if delay > 0:
            print(f'[{job_nr:8}] {job_name} - delay {delay} seconds', flush=True)
            time.sleep(delay)

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        pid = proc.pid
        CHILDREN[pid] = {'proc': proc}
        proc.stdin.write(stdin.encode('utf8'))
        proc.stdin.close()
        CHILDREN[pid]['job_nr'] = job_nr

        data['status'] = 'running'
        data['pid'] = pid
        cur.execute("""
            UPDATE tucal.job
            SET status = %(status)s, pid = %(pid)s
            WHERE job_nr = %(nr)s""", data)

        print(f'[{job_nr:8}] {job_name} - PID {pid} - {" ".join(cmd)}', flush=True)
        try:
            self.wfile.write(f'{pid}\n'.encode('utf8'))
        except BrokenPipeError:
            pass

        reader = tucal.JobStatus()
        data['time'] = reader.time
        data['start'] = reader.start.isoformat() if reader.start else None
        data['data'] = reader.json(),
        data['err'] = None

        cur.execute("""
            UPDATE tucal.job
            SET data = %(data)s,
                time = %(time)s,
                name = %(name)s
            WHERE job_nr = %(nr)s""", data)
        tucal.db.commit()

        code: int
        while True:
            code = proc.returncode
            if code is not None:
                break

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
                SET data = %(data)s,
                    status = %(status)s,
                    start_ts = %(start)s,
                    time = %(time)s,
                    name = %(name)s
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

        if code == 0:
            data['status'] = 'success'
        elif code > 0:
            data['status'] = 'error'
        else:
            data['status'] = 'aborted'

        try:
            self.wfile.write(f'status:{code}\n'.encode('utf8'))
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

        print(f'[{job_nr:8}] terminated ({code})', flush=True)
        del CHILDREN[pid]
        self.wfile.close()
        self.rfile.close()


class ThreadedUnixStreamServer(ThreadingMixIn, UnixStreamServer):
    pass


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_exit)
    signal.signal(signal.SIGHUP, signal_exit)
    signal.signal(signal.SIGABRT, signal_exit)
    signal.signal(signal.SIGTERM, signal_exit)

    cleanup_jobs()

    try:
        os.unlink('/var/tucal/scheduler.sock')
    except FileNotFoundError:
        pass
    with ThreadedUnixStreamServer('/var/tucal/scheduler.sock', Handler) as server:
        server.serve_forever()
