##
#: Console entry points. Each command is a grid calendar plus one or two holiday sources.
##
from .calendars import GREGORIAN, JALALI
from .cli import View, run_month_view
from .year_view import run_year_view

JCAL = View(calendar=JALALI, primary="iran")
GCAL_LMU = View(calendar=GREGORIAN, primary="lmu")


def jcal_all(argv=None) -> None:
    run_year_view(JCAL, argv=argv, description="All months of a Jalali year, with Iranian holidays.")


def gcal(argv=None) -> None:
    run_month_view(
        GCAL_LMU,
        argv=argv,
        description="A Gregorian month with holidays.",
        sources_option=True,
    )


def gcal_lmu(argv=None) -> None:
    run_month_view(GCAL_LMU, argv=argv, description="A Gregorian month with LMU Munich days off.")


def gcal_lmu_all(argv=None) -> None:
    run_year_view(
        GCAL_LMU,
        argv=argv,
        description="All months of a Gregorian year, with LMU Munich days off.",
        footnotes=True,
    )
