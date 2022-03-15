#!/bin/env python3

import argparse
import matplotlib.pyplot
import scipy.interpolate
import numpy as np


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str)
    args = parser.parse_args()

    rows = []
    with open(args.file, 'r') as f:
        f.readline()
        while True:
            line = f.readline()
            if not line:
                break
            rows.append([int(d) if d.isnumeric() else d if d != '' else None for d in line.strip().split(',')])

    rows.sort(key=lambda row: f'{row[0]}H{row[1]:02}')
    data = {(row[0], row[1]): row[2:] for row in rows}

    for i in range(2, len(rows[0])):
        x, y = [], []
        for j in range(len(rows)):
            row = rows[j]
            if not row[i]:
                continue
            x.append(j)
            y.append(row[i])

        matplotlib.pyplot.plot(x, y)

    matplotlib.pyplot.show()
