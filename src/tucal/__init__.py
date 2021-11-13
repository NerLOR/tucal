
from __future__ import annotations
import datetime


class Semester:
    _year: int
    _sem: str

    def __init__(self, semester: str):
        self._year = int(semester[:4])
        self._sem = semester[-1].upper()
        if self._sem not in 'WS':
            raise ValueError(f"invalid semester '{semester}'")

    def __int__(self) -> int:
        return self._year * 2 + (1 if self._sem == 'W' else 0)

    def __str__(self) -> str:
        return f'{self._year}{self._sem}'

    def __repr__(self) -> str:
        return f'{self._year}{self._sem}'

    def __eq__(self, other: Semester) -> bool:
        return self._year == other._year and self._sem == other._sem

    def __gt__(self, other: Semester) -> bool:
        return int(self) > int(other)

    def __lt__(self, other: Semester) -> bool:
        return int(self) < int(other)

    def __next__(self) -> Semester:
        return self + 1

    def __add__(self, other: int) -> Semester:
        c = int(self) + other
        return Semester(f'{c // 2}{"W" if c % 2 == 1 else "S"}')

    def __sub__(self, other: int) -> Semester:
        return self.__add__(-other)

    def __hash__(self) -> int:
        return int(self)

    @staticmethod
    def from_date(date: datetime.datetime) -> Semester:
        if date.month >= 10:
            return Semester(f'{date.year}W')
        elif date.month <= 2:
            return Semester(f'{date.year - 1}W')
        else:
            return Semester(f'{date.year}S')

    @staticmethod
    def current() -> Semester:
        return Semester.from_date(datetime.datetime.utcnow())

    @staticmethod
    def last() -> Semester:
        return Semester.current() - 1

    @staticmethod
    def next() -> Semester:
        return Semester.current() + 1
