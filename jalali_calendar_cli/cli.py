##
#: Command-line plumbing shared by every entry point.
##
import argparse
import datetime
import sys
from dataclasses import dataclass
from typing import Optional

from .model import build_month
from .render_ansi import COLOR_KEYS, DisplayOptions, format_month

#: Help texts for the per-key color options; `None` hides the option.
COLOR_HELP = {
    "weekend": "weekend color",
    "holiday": "holiday color",
    "footnote": None,
    "header": "header color",
    "today": "the current day's color",
    "shared": "color of days on which both shown holiday sets are free",
    "secondary_holiday": "background color of the second holiday set's holidays",
    "secondary_weekend": "background color of the second holiday set's weekend",
}


def add_display_args(parser, *, indentation=5, line_prefix=" ", footnotes=True):
    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="colorize the output",
    )

    # parser.add_argument(
    #     "--unicode",
    #     action=argparse.BooleanOptionalAction,
    #     default=True,
    #     help="enable Unicode superscript for footnote numbers",
    # )

    parser.add_argument(
        "--true-color",
        action=argparse.BooleanOptionalAction,
        # default=True,
        default=False,  #: to make the default compatible with dark themes
        help="enable true color support for output",
    )
    parser.add_argument(
        "--footnotes",
        action=argparse.BooleanOptionalAction,
        default=footnotes,
        help="show footnotes in the output",
    )
    parser.add_argument(
        "--indentation",
        type=int,
        default=indentation,
        help=f"number of spaces for indentation (default: {indentation})",
    )
    parser.add_argument(
        "--line-prefix",
        type=str,
        default=line_prefix,
        help=f"a prefix that is added to all lines of the output (default: {line_prefix!r})",
    )
    parser.add_argument(
        "--color-preset",
        choices=list(["light", "dark"]),
        default="light",
        help="color preset for the calendar output (default: light)",
    )

    true_color_group = parser.add_argument_group("24-bit true color options")
    colorama_color_group = parser.add_argument_group("colorama 256 color options")
    for key in COLOR_KEYS:
        help_text = COLOR_HELP.get(key)
        flag = key.replace("_", "-")
        true_color_group.add_argument(
            f"--{flag}-true-color",
            type=str,
            default=None,
            help=(f"RGB values for {help_text} in 24-bit true color" if help_text else argparse.SUPPRESS),
        )
        colorama_color_group.add_argument(
            f"--{flag}-color",
            type=str,
            default=None,
            help=(f"colorama color name for {help_text}" if help_text else argparse.SUPPRESS),
        )


def display_options_from_args(args) -> DisplayOptions:
    color = (args.color == "always") or (args.color == "auto" and sys.stdout.isatty())

    colors = dict()
    for color_key in COLOR_KEYS:
        if args.true_color:
            color_arg = getattr(args, f"{color_key}_true_color", None)
            if color_arg:
                colors[color_key] = {"true": tuple(map(int, color_arg.split(",")))}
        else:
            color_arg = getattr(args, f"{color_key}_color", None)
            if color_arg:
                colors[color_key] = {"name": color_arg.upper()}

    return DisplayOptions(
        color=color,
        true_color=args.true_color,
        color_preset=args.color_preset,
        color_overrides=colors,
        indentation=args.indentation,
        line_prefix=args.line_prefix,
        footnotes=args.footnotes,
    )


WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def parse_weekdays(text: str) -> frozenset:
    """"thu,fri" to Python weekdays (Monday is 0); "" means no weekend."""
    days = set()
    for part in text.split(","):
        part = part.strip().lower()[:3]
        if not part:
            continue
        if part not in WEEKDAY_NAMES:
            raise argparse.ArgumentTypeError(f"unknown weekday: {part!r}")
        days.add(WEEKDAY_NAMES.index(part))
    return frozenset(days)


def add_source_args(parser):
    group = parser.add_argument_group("holiday data")
    group.add_argument(
        "--holidays-json-path",
        type=str,
        default=None,
        help="path to JSON file containing Iranian holiday data (default: the bundled data, or $JALALI_HOLIDAYS_JSON_PATH)",
    )
    group.add_argument(
        "--iran-weekend",
        type=parse_weekdays,
        default="thu,fri",
        help="comma-separated weekdays that are the weekend in Iran (default: thu,fri; use 'fri' for the official reading)",
    )


def make_source(name: str, args):
    if name == "iran":
        from .sources.iran import IranSource

        return IranSource(
            holidays_json_path=args.holidays_json_path,
            weekend=args.iran_weekend,
        )

    raise ValueError(f"unknown holiday source: {name}")


@dataclass
class View:
    calendar: object
    primary: str
    secondary: Optional[str] = None


def run_month_view(view: View, argv=None, prog=None, description=None) -> None:
    parser = argparse.ArgumentParser(prog=prog, description=description)

    ##
    #: Get current date in the grid calendar
    now_year, now_month = view.calendar.today()
    calendar_name = view.calendar.name.capitalize()

    parser.add_argument(
        "month",
        type=int,
        nargs="?",
        default=now_month,
        help=f"month in {calendar_name} calendar (default: current month)",
    )
    parser.add_argument(
        "year",
        type=int,
        nargs="?",
        default=now_year,
        help=f"year in {calendar_name} calendar (default: current year)",
    )
    ##

    add_display_args(parser)
    add_source_args(parser)

    args = parser.parse_args(argv)
    opts = display_options_from_args(args)

    primary = make_source(view.primary, args)
    secondary = make_source(view.secondary, args) if view.secondary else None

    model = build_month(view.calendar, primary, secondary, args.year, args.month)
    sys.stdout.write(format_month(model, opts, today=datetime.date.today()))
