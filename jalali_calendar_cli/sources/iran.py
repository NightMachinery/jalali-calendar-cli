##
#: Iranian official holidays, from the bundled (or user-supplied) holidays JSON.
##
import datetime
import json
import os
import pathlib
from typing import Dict

import jdatetime

from ..calendars import JALALI

DEFAULT_HOLIDAYS_JSON_PATH = str(pathlib.Path(__file__).parent.parent / "holidays.json")

#: Python weekdays (Monday is 0).
#: Officially only Friday is the weekend (`holidays.Iran.weekend == {4}`), but Thursday is
#: off in practice for much of the country; a law making it official has been pending
#: since 2024. `--iran-weekend fri` gives the strict reading.
THURSDAY = 3
FRIDAY = 4
DEFAULT_WEEKEND = frozenset({THURSDAY, FRIDAY})


def default_holidays_json_path() -> str:
    return os.getenv("JALALI_HOLIDAYS_JSON_PATH") or DEFAULT_HOLIDAYS_JSON_PATH


class IranSource:
    tag = "IR"
    calendar = JALALI

    def __init__(self, holidays_json_path=None, weekend=DEFAULT_WEEKEND):
        self.holidays_json_path = holidays_json_path or default_holidays_json_path()
        self.weekend = frozenset(weekend)
        self._data = None

    @property
    def data(self) -> dict:
        if self._data is None:
            with open(self.holidays_json_path) as f:
                self._data = json.load(f)
        return self._data

    def jalali_year_events(self, year: int) -> Dict[datetime.date, str]:
        events = dict()
        for item in self.data.get(str(year), []):
            date = jdatetime.date(year, item["month"], item["day"]).togregorian()
            events[date] = item["event"]
        return events

    def events(self, start: datetime.date, end: datetime.date) -> Dict[datetime.date, str]:
        first_year = JALALI.from_gregorian(start)[0]
        last_year = JALALI.from_gregorian(end)[0]

        events = dict()
        for year in range(first_year, last_year + 1):
            events.update(self.jalali_year_events(year))

        return {date: name for date, name in events.items() if start <= date <= end}
