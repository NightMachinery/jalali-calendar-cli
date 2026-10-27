##
#: Command-line plumbing shared by every entry point.
##
import argparse
import datetime
import os
import shutil
import sys
from dataclasses import dataclass
from typing import Optional

from .calendars import next_month
from .model import build_month
from .render_ansi import COLOR_KEYS, DisplayOptions, fits_side_by_side, format_months

#: Help texts for the per-key color options; `None` hides the option.
COLOR_HELP = {
    "weekend": "weekend color",
    "holiday": "holiday color",
    "footnote": None,
    "header": "header color",
    "today": "the current day's color",
    "shared": "the background of days on which both shown holiday sets are free",
    "secondary_holiday": "the background of the second holiday set's holidays",
    "secondary_weekend": "the background of the second holiday set's weekend",
}


def add_display_args(parser, *, indentation=5, line_prefix=" ", footnotes=True, short_flags=False):
    #: The year view keeps the short flags of the old `jcal_all.pl`.
    def flags(short, long):
        return [short, long] if short_flags else [long]

    parser.add_argument(
        *flags("-c", "--color"),
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
        #: `None` detects it from the environment, see `terminal_supports_true_color`.
        default=None,
        help="use 24-bit colors (default: when the terminal advertises them)",
    )
    parser.add_argument(
        "--footnotes",
        action=argparse.BooleanOptionalAction,
        default=footnotes,
        help="show footnotes in the output",
    )
    parser.add_argument(
        *flags("-i", "--indentation"),
        type=int,
        default=indentation,
        help=f"number of spaces for indentation (default: {indentation})",
    )
    parser.add_argument(
        *flags("-p", "--line-prefix"),
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


#: Terminals known to support 24-bit color that do not always set `COLORTERM`.
TRUE_COLOR_TERM_PROGRAMS = frozenset({"iTerm.app", "WezTerm", "vscode", "ghostty"})
TRUE_COLOR_TERMS = frozenset({"xterm-kitty", "xterm-ghostty", "alacritty", "wezterm"})


def terminal_supports_true_color(environ=None) -> bool:
    """Whether the terminal advertises 24-bit color.

    `COLORTERM=truecolor` (or `24bit`) is the de facto convention; a `TERM` ending in
    `-direct` is terminfo's. The rest is a short list of terminals that support it
    without always saying so, e.g. when `COLORTERM` was lost over ssh or sudo.
    """
    if environ is None:
        environ = os.environ
    if environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return True
    term = environ.get("TERM", "")
    if term.endswith("-direct") or term in TRUE_COLOR_TERMS:
        return True
    return environ.get("TERM_PROGRAM", "") in TRUE_COLOR_TERM_PROGRAMS


def display_options_from_args(args) -> DisplayOptions:
    color = (args.color == "always") or (args.color == "auto" and sys.stdout.isatty())
    true_color = args.true_color
    if true_color is None:
        true_color = terminal_supports_true_color()

    colors = dict()
    for color_key in COLOR_KEYS:
        if true_color:
            color_arg = getattr(args, f"{color_key}_true_color", None)
            if color_arg:
                colors[color_key] = {"true": tuple(map(int, color_arg.split(",")))}
        else:
            color_arg = getattr(args, f"{color_key}_color", None)
            if color_arg:
                colors[color_key] = {"name": color_arg.upper()}

    return DisplayOptions(
        color=color,
        true_color=true_color,
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
        "--holidays-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="for years missing from the holidays JSON, compute Iranian holidays with the `holidays` package (lunar dates are estimates)",
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
            fallback=args.holidays_fallback,
        )

    if name == "lmu":
        from .sources.lmu import LmuSource

        return LmuSource()

    raise ValueError(f"unknown holiday source: {name}")


SOURCE_NAMES = ["iran", "lmu"]


def parse_sources(text: str):
    """"lmu,iran" to `(primary, secondary)`; the secondary is optional."""
    names = [name.strip().lower() for name in text.split(",") if name.strip()]
    if not 1 <= len(names) <= 2:
        raise argparse.ArgumentTypeError("give one or two holiday sources, e.g. lmu or lmu,iran")
    for name in names:
        if name not in SOURCE_NAMES:
            raise argparse.ArgumentTypeError(f"unknown holiday source: {name!r} (known: {', '.join(SOURCE_NAMES)})")
    return names[0], (names[1] if len(names) == 2 else None)


@dataclass
class View:
    calendar: object
    primary: str
    secondary: Optional[str] = None


def add_sources_arg(parser, view: View) -> None:
    """`--sources`, defaulting to the view's own holiday sets."""
    default_sources = ",".join(filter(None, [view.primary, view.secondary]))
    parser.add_argument(
        "--sources",
        type=parse_sources,
        default=default_sources,
        help=f"the holiday set to show, optionally followed by a second one to overlay, e.g. lmu,iran (known: {', '.join(SOURCE_NAMES)}; default: {default_sources})",
    )


def view_from_args(view: View, args) -> View:
    """The view with the holiday sets chosen by `--sources`, when the option exists."""
    sources = getattr(args, "sources", None)
    return View(view.calendar, *sources) if sources else view


def run_month_view(view: View, argv=None, prog=None, description=None, sources_option=False) -> None:
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
    parser.add_argument(
        "--next-month",
        choices=["auto", "always", "never"],
        default="auto",
        help="also show the following month, beside this one: auto when the terminal is wide enough for both (and when piped), always (below this one when it is not), or never (default: auto)",
    )

    add_display_args(parser)
    add_source_args(parser)
    if sources_option:
        add_sources_arg(parser, view)

    args = parser.parse_args(argv)
    opts = display_options_from_args(args)

    view = view_from_args(view, args)
    primary = make_source(view.primary, args)
    secondary = make_source(view.secondary, args) if view.secondary else None

    #: Only a terminal has a width to fit; piped output counts as wide enough.
    columns = shutil.get_terminal_size().columns if sys.stdout.isatty() else None

    models = [build_month(view.calendar, primary, secondary, args.year, args.month)]
    if args.next_month != "never":
        following = build_month(view.calendar, primary, secondary, *next_month(args.year, args.month))
        if args.next_month == "always" or fits_side_by_side([*models, following], opts, columns):
            models.append(following)

    sys.stdout.write(format_months(models, opts, today=datetime.date.today(), columns=columns))
