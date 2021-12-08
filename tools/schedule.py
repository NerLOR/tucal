#!/bin/env python3

import socket
import sys


if __name__ == '__main__':
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect('/var/tucal/scheduler.sock')
        client.send(' '.join(sys.argv[1:]).encode('utf8') + b'\n')
        msg = client.recv(64).strip().decode('utf8')
        if msg.startswith('error:'):
            print(f'Error: {msg[6:].strip()}')
            exit(1)

        job_nr, job_id, pid = msg.split(' ')
        client.close()
        print(job_nr, job_id, pid)
