#!/bin/env python3

import argparse
import sys
import matplotlib.pyplot


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str)
    args = parser.parse_args()

    with sys.stdin if args.file == '-' else open(args.file, 'r') as f:
        f.readline()
        data = [
            line[1:].split(':')
            for line in f.readlines()
            if line.startswith('*')
        ]
        data_y = [float(d[1]) * 100 for d in data]
        data_x = [float(d[0]) for d in data]

    matplotlib.pyplot.plot(data_x, data_y)
    matplotlib.pyplot.plot([0, data_x[-1]], [0, 100])
    matplotlib.pyplot.show()
