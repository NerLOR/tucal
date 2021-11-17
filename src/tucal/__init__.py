
from __future__ import annotations
import datetime
import typing


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
        return isinstance(other, Semester) and self._year == other._year and self._sem == other._sem

    def __gt__(self, other: Semester) -> bool:
        return int(self) > int(other)

    def __lt__(self, other: Semester) -> bool:
        return int(self) < int(other)

    def __next__(self) -> Semester:
        return self + 1

    def __add__(self, other: int) -> Semester:
        if isinstance(other, int):
            c = int(self) + other
            return Semester(f'{c // 2}{"W" if c % 2 == 1 else "S"}')
        else:
            raise ValueError(f'unable to add type {type(other)} to Semester')

    def __sub__(self, other: int or Semester) -> int or Semester:
        if isinstance(other, Semester):
            return int(self) - int(other)
        elif isinstance(other, int):
            return self.__add__(-other)
        else:
            raise ValueError(f'unable to subtract type {type(other)} from Semester')

    def __hash__(self) -> int:
        return int(self)

    @property
    def year(self) -> int:
        return self._year

    @property
    def sem(self) -> str:
        return self._sem

    @property
    def first_day(self) -> datetime.datetime:
        if self._sem == 'W':
            return datetime.datetime(year=self._year, month=10, day=1)
        else:
            return datetime.datetime(year=self._year, month=3, day=1)

    @property
    def last_day(self) -> datetime.datetime:
        return (self + 1).next().first_day - datetime.timedelta(seconds=1)

    @staticmethod
    def from_date(date: datetime.datetime) -> Semester:
        if date.month >= 10:
            return Semester(f'{date.year}W')
        elif date.month <= 2:
            return Semester(f'{date.year - 1}W')
        else:
            return Semester(f'{date.year}S')

    @staticmethod
    def from_date_strict(date: datetime.datetime) -> typing.Optional[Semester]:
        if date.month >= 10:
            return Semester(f'{date.year}W')
        elif date.month <= 1:
            return Semester(f'{date.year - 1}W')
        elif 3 <= date.month <= 6:
            return Semester(f'{date.year}S')
        else:
            return None

    @staticmethod
    def current() -> Semester:
        return Semester.from_date(datetime.datetime.utcnow())

    @staticmethod
    def last() -> Semester:
        return Semester.current() - 1

    @staticmethod
    def next() -> Semester:
        return Semester.current() + 1
