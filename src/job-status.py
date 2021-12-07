#!/bin/env python3

import argparse
import sys
import time

import tucal

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str)
    args = parser.parse_args()

    reader = tucal.JobStatus()

    with sys.stdin if args.file == '-' else open(args.file, 'r+') as f:
        while not reader.finished and not f.closed:
            line = f.readline()
            if not reader.line(line):
                time.sleep(0.125)
                continue

            if reader.get_current_step() is None:
                continue

            sec = reader.time
            perc = reader.progress * 100
            step = reader.get_current_step()

            steps = ' - '.join([f'{s["name"]} ({n}/{p})' for s, n, p in reader.path()])
            print(f'\r\x1B[2K', end='')
            print(f'{int(sec // 60):02}:{sec % 60:04.1f} - {perc:5.1f}% - {steps}: {step["name"][:100]} ', end='')
            print(reader.json())
            sys.stdout.flush()
        f.read()
        print()
