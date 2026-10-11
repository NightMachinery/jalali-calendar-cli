##
#: Days off for staff of LMU Munich (Ludwig-Maximilians-Universität München).
#:
#: - Bavarian public holidays, from the `holidays` package. Assumption Day (Aug 15) is a
#:   public holiday only in Bavarian municipalities with a predominantly Catholic
#:   population; Munich is one, so it is included (the package's "catholic" category).
#: - Dec 24 and Dec 31: TV-L § 6 Abs. 3 releases employees from work on these days with
#:   continued pay, when they fall on a working day.
#:
#: Not included, deliberately:
#: - Lecture-free days and lecture periods: these are not days off for staff.
#: - Shrove Tuesday (Faschingsdienstag): not a day off under TV-L; some units close at noon.
#: - Repentance Day (Buß- und Bettag): a school holiday in Bavaria, not a public holiday.
##
import datetime
from typing import Dict

from ..calendars import GREGORIAN

#: Python weekdays (Monday is 0)
SATURDAY = 5
SUNDAY = 6

TVL_DAYS_OFF = {
    (12, 24): "Christmas Eve (TV-L)",
    (12, 31): "New Year's Eve (TV-L)",
}


class LmuSource:
    tag = "LMU"
    label = "LMU"
    calendar = GREGORIAN
    weekend = frozenset({SATURDAY, SUNDAY})

    def __init__(self):
        self._years = dict()

    def year_events(self, year: int) -> Dict[datetime.date, str]:
        if year not in self._years:
            #: imported lazily: it costs ~65 ms, and jcal never needs it
            from holidays.countries.germany import Germany

            events = dict(
                Germany(
                    subdiv="BY",
                    years=year,
                    language="en_US",
                    categories=("public", "catholic"),
                )
            )
            for (month, day), name in TVL_DAYS_OFF.items():
                events[datetime.date(year, month, day)] = name

            self._years[year] = dict(sorted(events.items()))
        return self._years[year]

    def events(self, start: datetime.date, end: datetime.date) -> Dict[datetime.date, str]:
        events = dict()
        for year in range(start.year, end.year + 1):
            events.update(self.year_events(year))

        return {date: name for date, name in events.items() if start <= date <= end}
