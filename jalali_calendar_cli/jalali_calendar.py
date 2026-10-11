##
#: `jcal`: a Jalali month with Iranian holidays.
##
from .calendars import JALALI, get_jalali_days, jmonth_name  # noqa: F401 (re-exported)
from .cli import View, run_month_view

JCAL = View(calendar=JALALI, primary="iran")


def main(args=None) -> None:
    #: `args` is the argument list without the program name; None means `sys.argv[1:]`.
    run_month_view(JCAL, argv=args)


if __name__ == "__main__":
    main()
