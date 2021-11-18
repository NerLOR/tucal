#!/bin/env python3

import argparse
import sys
import time


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str)
    args = parser.parse_args()

    sub = []
    with sys.stdin if args.file == '-' else open(args.file, 'r+') as f:
        f.readline()
        name = None
        end = False
        while not end:
            line = f.readline()
            if len(line) == 0:
                time.sleep(0.125)
                continue
            line = line.strip()
            if len(line) == 0:
                continue
            elif not line.startswith('*'):
                print('\r\x1B[2K' + line)
                continue

            line = line[1:].split(':', 4)
            sec = float(line[0])
            perc = float(line[1]) * 100
            mode = line[2]

            if mode == 'START':
                n = int(line[3])
                name = line[4]
                if len(sub) > 0:
                    sub[-1][1] += 1
                if n > 0:
                    sub.append([name, 0, int(n)])
            elif mode == 'STOP' and sub[-1][1] == sub[-1][2]:
                s = sub.pop(-1)
                name = s[0]
                if len(sub) == 0:
                    sub = [s]
                    end = True

            steps = ' - '.join([f'{s[0]} ({s[1]}/{s[2]})' for s in sub])
            print(f'\r\x1B[2K{int(sec // 60):02}:{sec % 60:04.1f} - {perc:5.1f}% - {steps}: {name[:100]} ', end='')
            sys.stdout.flush()
        f.read()
        print()
