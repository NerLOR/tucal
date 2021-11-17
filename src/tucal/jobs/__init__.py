
from __future__ import annotations
import datetime
import time
import sys


class Job:
    perc_steps: int
    _n: int
    _name: str
    _proc_start: float
    _clock_id: int

    def __init__(self, name: str, sub_steps: int, perc_steps: int = 1):
        self.perc_steps = perc_steps
        self._n = 0
        self._name = name
        self._clock_id = time.CLOCK_MONOTONIC
        self._proc_start = time.clock_gettime(self._clock_id)
        print(f'**{datetime.datetime.utcnow().isoformat()}')
        print(f'*{self._format_time()}:0.0000:START:{sub_steps}:{name}')
        sys.stdout.flush()

    def begin(self, name: str, sub_steps: int = 0):
        print(f'*{self._format_time()}:{self._n / self.perc_steps:.4f}:START:{sub_steps}:{name}')
        sys.stdout.flush()

    def end(self, steps: int):
        self._n += steps
        print(f'*{self._format_time()}:{self._n / self.perc_steps:.4f}:STOP')
        sys.stdout.flush()

    def sub_stop(self, steps: int):
        self._n += steps

    def _format_time(self) -> str:
        return f'{time.clock_gettime(self._clock_id) - self._proc_start:7.2f}'
