##
#: Grid calendars. Each one knows how to lay out a month and how to convert its dates
#: to and from Gregorian `datetime.date`s, which is what holiday sources are keyed by.
##
import calendar as stdlib_calendar
import datetime
from typing import Tuple

import jdatetime

JALALI_MONTH_NAMES = [
    "Farvardin",
    "Ordibehesht",
    "Khordad",
    "Tir",
    "Mordad",
    "Shahrivar",
    "Mehr",
    "Aban",
    "Azar",
    "Dey",
    "Bahman",
    "Esfand",
]

GREGORIAN_MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def jmonth_name(month: int) -> str:
    if 1 <= month <= 12:
        return JALALI_MONTH_NAMES[month - 1]
    else:
        raise ValueError("Month must be between 1 and 12 inclusive")


def get_jalali_days(year: int, month: int) -> int:
    if month <= 6:
        num_days = 31
    elif month <= 11:
        num_days = 30
    else:  # Esfand
        j_date = jdatetime.date(year, month, 1)
        num_days = 29 if not j_date.isleap() else 30
    return num_days


def _span(first: Tuple[int, str], last: Tuple[int, str]) -> str:
    """`(year, month_name)` pairs to "Mehr–Aban 1405" or "Esfand 1404–Farvardin 1405"."""
    (first_year, first_month), (last_year, last_month) = first, last
    if first == last:
        return f"{first_month} {first_year}"
    if first_year == last_year:
        return f"{first_month}–{last_month} {first_year}"
    return f"{first_month} {first_year}–{last_month} {last_year}"


class JalaliCalendar:
    name = "jalali"
    #: Saturday first
    weekday_names = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]

    def month_range(self, year: int, month: int) -> Tuple[int, int]:
        """`(column of the first day, number of days)`."""
        return jdatetime.date(year, month, 1).weekday(), get_jalali_days(year, month)

    def to_gregorian(self, year: int, month: int, day: int) -> datetime.date:
        return jdatetime.date(year, month, day).togregorian()

    def from_gregorian(self, date: datetime.date) -> Tuple[int, int, int]:
        j = jdatetime.date.fromgregorian(date=date)
        return j.year, j.month, j.day

    def weekday_column(self, weekday: int) -> int:
        """Python weekday (Monday is 0) to grid column."""
        return (weekday + 2) % 7

    def month_name(self, month: int) -> str:
        return jmonth_name(month)

    def title(self, year: int, month: int) -> str:
        return f"{year} {jmonth_name(month)}"

    def short_date(self, date: datetime.date) -> str:
        _, month, day = self.from_gregorian(date)
        return f"{day} {jmonth_name(month)}"

    def span(self, start: datetime.date, end: datetime.date) -> str:
        y1, m1, _ = self.from_gregorian(start)
        y2, m2, _ = self.from_gregorian(end)
        return _span((y1, jmonth_name(m1)), (y2, jmonth_name(m2)))

    def today(self) -> Tuple[int, int]:
        now = jdatetime.date.today()
        return now.year, now.month


class GregorianCalendar:
    name = "gregorian"
    #: Monday first, as in Germany and ISO 8601
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def month_range(self, year: int, month: int) -> Tuple[int, int]:
        return stdlib_calendar.monthrange(year, month)

    def to_gregorian(self, year: int, month: int, day: int) -> datetime.date:
        return datetime.date(year, month, day)

    def from_gregorian(self, date: datetime.date) -> Tuple[int, int, int]:
        return date.year, date.month, date.day

    def weekday_column(self, weekday: int) -> int:
        return weekday

    def month_name(self, month: int) -> str:
        return GREGORIAN_MONTH_NAMES[month - 1]

    def title(self, year: int, month: int) -> str:
        return f"{year} {self.month_name(month)}"

    def short_date(self, date: datetime.date) -> str:
        return f"{date.day} {self.month_name(date.month)[:3]}"

    def span(self, start: datetime.date, end: datetime.date) -> str:
        return _span(
            (start.year, self.month_name(start.month)),
            (end.year, self.month_name(end.month)),
        )

    def today(self) -> Tuple[int, int]:
        now = datetime.date.today()
        return now.year, now.month


JALALI = JalaliCalendar()
GREGORIAN = GregorianCalendar()
