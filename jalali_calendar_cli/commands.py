##
#: Console entry points. Each command is a grid calendar plus one or two holiday sources.
##
from .calendars import JALALI
from .cli import View
from .year_view import run_year_view

JCAL = View(calendar=JALALI, primary="iran")


def jcal_all(argv=None) -> None:
    run_year_view(JCAL, argv=argv, description="All months of a Jalali year, with Iranian holidays.")
