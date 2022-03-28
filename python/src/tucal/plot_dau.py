#!/bin/env python3

import argparse
import datetime
import matplotlib.pyplot
from matplotlib.colors import hsv_to_rgb

import tucal.db

AVG_VAL = 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.parse_args()

    cur = tucal.db.cursor()
    cur.execute("SELECT * FROM tucal.v_dau_daily")
    data = cur.fetch_all()
    dau = []
    for i in range(len(data)):
        date: datetime.date
        date, users_day, users_week, users = data[i]
        p = data[max(i - AVG_VAL, 0):min(i + AVG_VAL + 1, len(data))]
        avg = sum([v[1] for v in p]) / len(p)
        dau.append((avg, users_day, users_week, users))

    c_b1 = hsv_to_rgb((0.3333, 0.75, 0.5))
    c_b2 = hsv_to_rgb((0.3333, 0.75, 0.675))
    c1 = hsv_to_rgb((0.6667, 0.75, 0.75))
    c2 = hsv_to_rgb((0.6667, 0.5, 1))
    c2_l = (*c2, 0.25)
    d1 = [d[3] for d in dau]
    d2 = [d[2] for d in dau]
    d3 = [d[1] for d in dau]
    d4 = [d[0] for d in dau]

    fig: matplotlib.pyplot.Figure = matplotlib.pyplot.figure()
    plt = fig.add_subplot()

    dates = [d[0] for d in data]
    plt.fill_between(dates, d1, color=c_b1)
    l1, = plt.plot(dates, d1, color=c_b1, label='Verified users')
    plt.fill_between(dates, d2, color=c_b2)
    l2, = plt.plot(dates, d2, color=c_b2, label='Active users (last 7 days)')
    plt.fill_between(dates, d3, color=c1)
    l3, = plt.plot(dates, d3, color=c1, label='Daily active users')
    plt.fill_between(dates, d3, d4, color=c2_l)
    l4, = plt.plot(dates, d4, color=c2, linewidth=2, label='Daily active users (7-day average)')

    plt.legend(handles=[l1, l2, l3, l4])
    fig.set_dpi(150)
    fig.tight_layout()
    matplotlib.pyplot.show()
