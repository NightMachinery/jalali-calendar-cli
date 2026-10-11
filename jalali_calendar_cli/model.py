##
#: The month model: everything about a month that the formatters (terminal, HTML) need,
#: decided once. It holds no colors and no layout, only facts.
##
import datetime
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WeekdayLabel:
    text: str
    primary_weekend: bool = False
    secondary_weekend: bool = False


@dataclass
class Cell:
    day: int
    #: 0 is the first column of the grid
    column: int
    date: datetime.date
    primary_holiday: bool = False
    primary_weekend: bool = False
    secondary_holiday: bool = False
    secondary_weekend: bool = False
    #: whether a secondary source is shown at all
    overlay: bool = False

    @property
    def primary_free(self) -> bool:
        return self.primary_holiday or self.primary_weekend

    @property
    def secondary_free(self) -> bool:
        return self.secondary_holiday or self.secondary_weekend

    @property
    def both_free(self) -> bool:
        return self.overlay and self.primary_free and self.secondary_free


@dataclass
class Footnote:
    day: int
    name: str
    #: the source's tag; only set when two sources are shown
    tag: Optional[str] = None
    #: the date in the source's own calendar, for secondary entries
    note: Optional[str] = None
    secondary: bool = False


@dataclass
class MonthModel:
    year: int
    month: int
    title: str
    #: the other calendar's span, when a secondary source is shown
    subtitle: Optional[str]
    #: the same, abbreviated and without years, for a title on one line
    short_subtitle: Optional[str]
    weekday_labels: List[WeekdayLabel]
    first_column: int
    cells: List[Cell]
    footnotes: List[Footnote] = field(default_factory=list)


def build_month(calendar, primary, secondary, year: int, month: int) -> MonthModel:
    """
    Builds the model of one month of `calendar` (the grid calendar).

    `primary` and `secondary` are holiday sources; `secondary` may be None.
    """
    first_column, num_days = calendar.month_range(year, month)
    dates = [calendar.to_gregorian(year, month, day) for day in range(1, num_days + 1)]
    start, end = dates[0], dates[-1]

    primary_events = primary.events(start, end)
    secondary_events = secondary.events(start, end) if secondary else {}

    primary_weekend_cols = {calendar.weekday_column(wd) for wd in primary.weekend}
    secondary_weekend_cols = (
        {calendar.weekday_column(wd) for wd in secondary.weekend} if secondary else set()
    )
    overlay = secondary is not None

    labels = [
        WeekdayLabel(
            text=name,
            primary_weekend=(col in primary_weekend_cols),
            secondary_weekend=(col in secondary_weekend_cols),
        )
        for col, name in enumerate(calendar.weekday_names)
    ]

    cells = []
    footnotes = []
    for day, date in enumerate(dates, start=1):
        column = (first_column + day - 1) % 7
        cells.append(
            Cell(
                day=day,
                column=column,
                date=date,
                primary_holiday=(date in primary_events),
                primary_weekend=(column in primary_weekend_cols),
                secondary_holiday=(date in secondary_events),
                secondary_weekend=(column in secondary_weekend_cols),
                overlay=overlay,
            )
        )
        if date in primary_events:
            footnotes.append(
                Footnote(
                    day=day,
                    name=primary_events[date],
                    tag=(primary.tag if overlay else None),
                )
            )
        if date in secondary_events:
            footnotes.append(
                Footnote(
                    day=day,
                    name=secondary_events[date],
                    tag=secondary.tag,
                    note=secondary.calendar.short_date(date),
                    secondary=True,
                )
            )

    subtitle = secondary.calendar.span(start, end) if overlay else None
    short_subtitle = secondary.calendar.short_span(start, end) if overlay else None

    return MonthModel(
        year=year,
        month=month,
        title=calendar.title(year, month),
        subtitle=subtitle,
        short_subtitle=short_subtitle,
        weekday_labels=labels,
        first_column=first_column,
        cells=cells,
        footnotes=footnotes,
    )
