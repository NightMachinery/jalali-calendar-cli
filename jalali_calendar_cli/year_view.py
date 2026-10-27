##
#: The year view: all twelve months in a grid, three per row.
#: Formerly `jcal_all.pl`, which ran `jcal` once per month.
##
import argparse
import datetime
import sys
from typing import List, Optional

from .model import MonthModel, build_month
from .render_ansi import DisplayOptions, month_footnotes, month_lines, side_by_side


def render_year(
    models: List[MonthModel],
    opts: DisplayOptions,
    calendar,
    today: Optional[datetime.date] = None,
    outer_indent: int = 2,
    horizontal_indent: int = 1,
    months_per_row: int = 3,
    footnotes: bool = False,
) -> str:
    #: The months themselves never carry footnotes; the year's list goes at the end.
    #: Titles go on one line, so that four rows of months fit a terminal.
    grid_opts = DisplayOptions(**{**opts.__dict__, "footnotes": False, "one_line_title": True})

    out = []
    rows = [models[i : i + months_per_row] for i in range(0, len(models), months_per_row)]
    for row_index, row in enumerate(rows):
        #: =calendars= is a list (months) of list of strings (rows of each month).
        calendars = [month_lines(model, grid_opts, today) for model in row]
        out.extend(line + "\n" for line in side_by_side(calendars, outer_indent))

        #: no separator after the last row
        if row_index < len(rows) - 1:
            out.append("\n" * horizontal_indent)

    if footnotes:
        lines = month_footnotes(models, calendar, opts.line_prefix)
        if lines:
            out.append(f"\n{opts.line_prefix}Holidays:\n")
            out.append("\n".join(lines) + "\n")

    return "".join(out)


def run_year_view(view, argv=None, prog=None, description=None, footnotes=False, sources_option=False) -> None:
    from .cli import (
        add_display_args,
        add_source_args,
        add_sources_arg,
        display_options_from_args,
        make_source,
        view_from_args,
    )

    parser = argparse.ArgumentParser(prog=prog, description=description)
    now_year, _ = view.calendar.today()
    calendar_name = view.calendar.name.capitalize()
    parser.add_argument(
        "year",
        type=int,
        nargs="?",
        default=now_year,
        help=f"year in {calendar_name} calendar (default: current year)",
    )

    #: Perl's defaults: tighter cells and no line prefix, since we need the screen real estate.
    add_display_args(parser, indentation=4, line_prefix="", footnotes=footnotes, short_flags=True)
    parser.add_argument(
        "-o",
        "--outer-indent",
        type=int,
        default=2,
        help="spaces between months (default: 2)",
    )
    parser.add_argument(
        "--horizontal-indent",
        type=int,
        default=1,
        help="blank lines between rows of months (default: 1)",
    )
    add_source_args(parser)
    if sources_option:
        add_sources_arg(parser, view)

    args = parser.parse_args(argv)
    opts = display_options_from_args(args)

    view = view_from_args(view, args)

    primary = make_source(view.primary, args)
    secondary = make_source(view.secondary, args) if view.secondary else None

    models = [build_month(view.calendar, primary, secondary, args.year, month) for month in range(1, 13)]
    sys.stdout.write(
        render_year(
            models,
            opts,
            view.calendar,
            today=datetime.date.today(),
            outer_indent=args.outer_indent,
            horizontal_indent=args.horizontal_indent,
            footnotes=args.footnotes,
        )
    )
