##
#: Console entry points. Each command is a grid calendar plus one or two holiday sources.
##
from .calendars import GREGORIAN, JALALI
from .cli import View, run_month_view
from .year_view import run_year_view

JCAL = View(calendar=JALALI, primary="iran")
GCAL_LMU = View(calendar=GREGORIAN, primary="lmu")
#: Overlay views: text colors show the first set, backgrounds the second.
GCAL_LMU_IRAN = View(calendar=GREGORIAN, primary="lmu", secondary="iran")
JCAL_IRAN_LMU = View(calendar=JALALI, primary="iran", secondary="lmu")


def jcal_all(argv=None) -> None:
    run_year_view(JCAL, argv=argv, description="All months of a Jalali year, with Iranian holidays.")


def gcal(argv=None) -> None:
    run_month_view(
        GCAL_LMU,
        argv=argv,
        description="A Gregorian month with holidays.",
        sources_option=True,
    )


def gcal_all(argv=None) -> None:
    run_year_view(
        GCAL_LMU,
        argv=argv,
        description="All months of a Gregorian year, with holidays.",
        sources_option=True,
    )


def gcal_lmu(argv=None) -> None:
    run_month_view(GCAL_LMU, argv=argv, description="A Gregorian month with LMU Munich days off.")


def gcal_lmu_all(argv=None) -> None:
    run_year_view(
        GCAL_LMU,
        argv=argv,
        description="All months of a Gregorian year, with LMU Munich days off.",
    )


def gcal_lmu_iran(argv=None) -> None:
    run_month_view(
        GCAL_LMU_IRAN,
        argv=argv,
        description="A Gregorian month with LMU Munich days off, overlaid with Iranian holidays.",
    )


def gcal_lmu_iran_all(argv=None) -> None:
    run_year_view(
        GCAL_LMU_IRAN,
        argv=argv,
        description="All months of a Gregorian year, with LMU Munich days off overlaid with Iranian holidays.",
    )


def jcal_iran_lmu(argv=None) -> None:
    run_month_view(
        JCAL_IRAN_LMU,
        argv=argv,
        description="A Jalali month with Iranian holidays, overlaid with LMU Munich days off.",
    )


def jcal_iran_lmu_all(argv=None) -> None:
    run_year_view(
        JCAL_IRAN_LMU,
        argv=argv,
        description="All months of a Jalali year, with Iranian holidays overlaid with LMU Munich days off.",
    )
