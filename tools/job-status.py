#!/bin/env python3

import argparse
import sys


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    sub = []
    sys.stdin.readline()
    name = None
    end = False
    while not end and not sys.stdin.closed and sys.stdin.readable():
        line = sys.stdin.readline().strip()
        if len(line) == 0:
            break
        if not line.startswith('*'):
            print('\r\x1B[2K' + line)
            continue
        line = line[1:].split(':')
        sec = float(line[0])
        perc = float(line[1]) * 100
        mode = line[2]
        if mode == 'START':
            n = int(line[3])
            name = line[4]
            if n == 0:
                sub[-1][1] += 1
            else:
                sub.append([name, 0, int(n)])
        elif mode == 'STOP' and sub[-1][1] == sub[-1][2]:
            s = sub.pop(-1)
            name = s[0]
            if len(sub) == 0:
                sub = [s]
                end = True
            else:
                sub[-1][1] += 1
        steps = ' - '.join([f'{s[0]} ({s[1]}/{s[2]})' for s in sub])
        print(f'\r\x1B[2K{int(sec // 60):02}:{sec % 60:04.1f} - {perc:5.1f}% - {steps}: {name}', end='')
        sys.stdout.flush()
    sys.stdin.read()
    print()
