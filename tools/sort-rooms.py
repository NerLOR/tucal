#!/bin/env python3

import argparse
import re

NAME_REPLACE = re.compile(r'[^A-Za-z0-9äüößÄÜÖẞ]')
NUMBERS = re.compile(r'[0-9]+')


def key(r, h) -> str:
    return r[h['type']][:3].lower() + \
           r[h['room_codes']][0][0].lower() + \
           NUMBERS.sub(lambda m: ('0000' + m.group(0))[-4:], NAME_REPLACE.sub('', r[h['name']]).lower())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str)
    args = parser.parse_args()

    with open(args.file, 'r') as f:
        data = [line.split(',') for line in f.readlines()]

    first = data[0]
    head = {title: data[0].index(title) for title in data[0]}
    data = data[1:]

    data.sort(key=lambda d: key(d, head))

    with open(args.file, 'w') as f:
        f.write(','.join(first))
        for row in data:
            f.write(','.join(row))
