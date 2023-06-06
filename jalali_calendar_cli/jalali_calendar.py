##
import pathlib
from typing import List
import sys
import jdatetime
import datetime
import json
import os
import argparse
import colorama
from colorama import Fore, Style, init

try:
    from icecream import ic, colorize as ic_colorize

    ic.configureOutput(outputFunction=lambda s: print(ic_colorize(s)))
except ImportError:
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)


init(autoreset=False)


# Color presets for different themes
COLOR_PRESETS = {
    "light": {
        "weekend": {"name": "LIGHTMAGENTA_EX", "true": (85, 26, 139)},
        "holiday": {"name": "LIGHTRED_EX", "true": (230, 69, 0)},
        "footnote": {"name": "LIGHTBLACK_EX", "true": (170, 170, 170)},
        "header": {"name": "BLACK", "true": (50, 50, 50)},
    },
    "dark": {
        "weekend": {"name": "LIGHTMAGENTA_EX", "true": (255, 0, 255)},
        "holiday": {"name": "LIGHTRED_EX", "true": (255, 0, 0)},
        "footnote": {"name": "LIGHTBLACK_EX", "true": (128, 128, 128)},
        "header": {"name": "WHITE", "true": (255, 255, 255)},
    },
}


def jmonth_name(month: int) -> str:
    month_names = [
        "Farvardin",
        "Ordibehesht",
        "Khordad",
        "Tir",
        "Mordad",
        "Shahrivar",
        "Mehr",
        "Aban",
        "Azar",
        "Dey",
        "Bahman",
        "Esfand",
    ]

    if 1 <= month <= 12:
        return month_names[month - 1]
    else:
        raise ValueError("Month must be between 1 and 12 inclusive")


def center_justify(string, width):
    if len(string) >= width:
        return string  # No need for justification if string is already wider or equal to width

    spaces = width - len(string)
    left_spaces = spaces // 2
    right_spaces = spaces - left_spaces

    justified_string = " " * left_spaces + string + " " * right_spaces
    return justified_string


def prefix_lines(text, prefix=""):
    lines = text.split("\n")  # Split text into lines
    prefixed_lines = [prefix + line for line in lines]  # Add prefix to each line
    return "\n".join(prefixed_lines)  # Join lines back into text with prefixed lines


def generate_true_color_code(red: int, green: int, blue: int) -> str:
    """
    Generates ANSI escape code for 24-bit true colors.

    Args:
        red (int): The intensity of the red color component (0-255).
        green (int): The intensity of the green color component (0-255).
        blue (int): The intensity of the blue color component (0-255).

    Returns:
        str: The ANSI escape code for the specified true color.

    """

    # ANSI escape code format: \x1b[38;2;<r>;<g>;<b>m
    escape_code = f"\x1b[38;2;{red};{green};{blue}m"
    return escape_code


def get_jalali_days(year: int, month: int) -> int:
    if month <= 6:
        num_days = 31
    elif month <= 11:
        num_days = 30
    else:  # Esfand
        j_date = jdatetime.date(year, month, 1)
        num_days = 29 if not j_date.isleap() else 30
    return num_days


def generate_calendar(
    year: int,
    month: int,
    first_day_of_month: int,
    num_days: int,
    holidays: dict,
    indentation: int = 5,
    color: bool = False,
    unicode_p: bool = True,
    true_color: bool = False,
    color_preset: str = "light",
    weekend_color=None,
    holiday_color=None,
    footnote_color=None,
    header_color=None,
) -> List[str]:
    assert indentation >= 4

    weekdays = [
        "Sat",
        "Sun",
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
    ]
    header_indentation_len = indentation - 3
    blank1 = " " * indentation
    calendar = [blank1 * (first_day_of_month)]
    footnotes = []
    superscript_map = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

    # Get color preset
    preset = COLOR_PRESETS[color_preset]

    # Determine color options
    weekend_color = weekend_color if weekend_color else preset["weekend"]
    holiday_color = holiday_color if holiday_color else preset["holiday"]
    footnote_color = footnote_color if footnote_color else preset["footnote"]
    header_color = header_color if header_color else preset["header"]

    # Determine color start values
    if true_color:
        weekend_color_ansi = generate_true_color_code(*weekend_color["true"])
        holiday_color_ansi = generate_true_color_code(*holiday_color["true"])
        footnote_color_ansi = generate_true_color_code(*footnote_color["true"])
        header_color_ansi = generate_true_color_code(*header_color["true"])
    else:
        weekend_color_ansi = getattr(colorama.Fore, weekend_color["name"])
        holiday_color_ansi = getattr(colorama.Fore, holiday_color["name"])
        footnote_color_ansi = getattr(colorama.Fore, footnote_color["name"])
        header_color_ansi = getattr(colorama.Fore, header_color["name"])

    bold_ansi = Style.BRIGHT if color else ""
    reset_color = Style.RESET_ALL if color else ""

    last_indentation_debt = header_indentation_len
    for day in range(1, num_days + 1):
        weekday = (day + first_day_of_month) % 7
        day_str = str(day)
        day_str = day_str.rjust(indentation - last_indentation_debt)
        last_indentation_debt = 0

        if day in holidays:
            footnotes.append(f"{day:2d}: {holidays[day]}")

            if (
                False
            ):  #: @cruft no need to use footnotes when the days can act as indices already
                footnotes.append(f"{len(footnotes)+1:2d}: {holidays[day]}")
                footnote_num_str = str(len(footnotes))
                if unicode_p:
                    footnote_num_str = footnote_num_str.translate(superscript_map)
                else:
                    footnote_num_str = f"[{footnote_num_str}]"

                last_indentation_debt += len(footnote_num_str)
            else:
                footnote_num_str = ""

            day_str = f"{bold_ansi}{holiday_color_ansi}{day_str}{reset_color}"
            if footnote_num_str:
                day_str += f"{footnote_color_ansi}{footnote_num_str}{reset_color}"

        elif weekday == 0:
            day_str = f"{weekend_color_ansi}{day_str}{reset_color}"

        # ic(indentation, day_str, day_str.rjust(indentation))
        calendar.append(day_str)

        if weekday == 0:
            calendar.append("\n")
            last_indentation_debt = header_indentation_len

    headers_weekdays = (" " * header_indentation_len).join(weekdays)

    headers = ""
    year_month_str = f"{year} {jmonth_name(month)}"
    headers += f"{bold_ansi}{header_color_ansi}{center_justify(year_month_str, len(headers_weekdays))}{reset_color}\n"
    headers += f"{bold_ansi}{headers_weekdays}{reset_color}"

    return f"{headers}\n{''.join(calendar)}", "\n".join(footnotes)


def load_holidays(holidays_data, year: int, month: int) -> dict:
    year_str = str(year)
    if year_str in holidays_data:
        holidays_year = holidays_data[year_str]
        holidays = {
            item["day"]: item["event"]
            for item in holidays_year
            if item["month"] == month
        }
        return holidays
    else:
        return dict()


def jalali_calendar(
    year: int,
    month: int,
    color: bool,
    unicode_p: bool,
    indentation: int,
    true_color: bool,
    holidays_data,
    footnotes_p: bool = True,
    color_preset: str = "light",
    weekend_color=None,
    holiday_color=None,
    footnote_color=None,
    header_color=None,
) -> None:
    j_date = jdatetime.date(year, month, 1)
    first_day_of_month = j_date.weekday()
    num_days = get_jalali_days(year, month)
    holidays = load_holidays(holidays_data, year, month)
    calendar, footnotes = generate_calendar(
        year,
        month,
        first_day_of_month,
        num_days,
        holidays,
        indentation=indentation,
        color=color,
        unicode_p=unicode_p,
        true_color=true_color,
        color_preset=color_preset,
        weekend_color=weekend_color,
        holiday_color=holiday_color,
        footnote_color=footnote_color,
        header_color=header_color,
    )
    line_indent = " "
    calendar = prefix_lines(calendar, prefix=line_indent)
    print(calendar)

    if footnotes_p:
        footnotes = prefix_lines(footnotes, prefix=f"{line_indent}  ")

        print(f"\n{line_indent}Holidays:")
        print(footnotes)


def main(args=None) -> None:
    if args is None:
        args = sys.argv

    default_holiday_data_json_path = os.getenv("JALALI_HOLIDAYS_JSON_PATH") or str(
        pathlib.Path(__file__).parent / "holidays.json"
    )
    # ic(default_holiday_data_json_path)

    parser = argparse.ArgumentParser()

    ##
    # Get current Jalali date
    now = datetime.datetime.now()
    now_jalali = jdatetime.datetime.now()

    parser.add_argument(
        "month",
        type=int,
        nargs="?",
        default=now_jalali.month,
        help="month in Jalali calendar (default: current month)",
    )
    parser.add_argument(
        "year",
        type=int,
        nargs="?",
        default=now_jalali.year,
        help="year in Jalali calendar (default: current year)",
    )
    ##
    # parser.add_argument("month", type=int, help="Month in Jalali calendar")
    # parser.add_argument("year", type=int, help="Year in Jalali calendar")
    ##

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
        default=True,
        help="show footnotes in the output",
    )
    parser.add_argument(
        "--indentation",
        type=int,
        default=5,
        help="number of spaces for indentation (default: 5)",
    )
    parser.add_argument(
        "--holidays-json-path",
        type=str,
        default=default_holiday_data_json_path,
        help="path to JSON file containing holiday data",
    )

    parser.add_argument(
        "--color-preset",
        choices=["light", "dark",],
        default="light",
        help="color preset for the calendar output (default: light)",
    )

    true_color_group = parser.add_argument_group("24-bit true color options")
    true_color_group.add_argument(
        "--weekend-true-color",
        type=str,
        default=None,
        help="RGB values for weekend color in 24-bit true color",
    )
    true_color_group.add_argument(
        "--holiday-true-color",
        type=str,
        default=None,
        help="RGB values for holiday color in 24-bit true color",
    )
    true_color_group.add_argument(
        "--footnote-true-color",
        type=str,
        default=None,
        # help="RGB values for footnote color in 24-bit true color",
        help=argparse.SUPPRESS,
    )
    true_color_group.add_argument(
        "--header-true-color",
        type=str,
        default=None,
        help="RGB values for header color in 24-bit true color",
    )

    colorama_color_group = parser.add_argument_group("colorama 256 color options")
    colorama_color_group.add_argument(
        "--weekend-color",
        type=str,
        default=None,
        help="colorama color name for weekend color",
    )
    colorama_color_group.add_argument(
        "--holiday-color",
        type=str,
        default=None,
        help="colorama color name for holiday color",
    )
    colorama_color_group.add_argument(
        "--footnote-color",
        type=str,
        default=None,
        # help="colorama color name for footnote color",
        help=argparse.SUPPRESS,
    )
    colorama_color_group.add_argument(
        "--header-color",
        type=str,
        default=None,
        help="colorama color name for header color",
    )

    args = parser.parse_args()

    color = args.color == "always" or (args.color == "auto" and sys.stdout.isatty())

    colors = dict()
    color_keys = ["weekend", "holiday", "footnote", "header"]
    if args.true_color:
        for color_key in color_keys:
            color_arg = getattr(args, f"{color_key}_true_color", None)
            if color_arg:
                if color_key not in colors:
                    colors[color_key] = dict()
                colors[color_key]["true"] = tuple(map(int, color_arg.split(",")))
    else:
        for color_key in color_keys:
            color_arg = getattr(args, f"{color_key}_color", None)
            if color_arg:
                if color_key not in colors:
                    colors[color_key] = dict()
                colors[color_key]["name"] = color_arg.upper()

    weekend_color = colors.get("weekend", None)
    holiday_color = colors.get("holiday", None)
    footnote_color = colors.get("footnote", None)
    header_color = colors.get("header", None)

    unicode_p = True
    # unicode_p = args.unicode

    with open(args.holidays_json_path) as f:
        holidays_data = json.load(f)

    jalali_calendar(
        args.year,
        args.month,
        color,
        unicode_p,
        args.indentation,
        args.true_color,
        holidays_data=holidays_data,
        footnotes_p=args.footnotes,
        color_preset=args.color_preset,
        weekend_color=weekend_color,
        holiday_color=holiday_color,
        footnote_color=footnote_color,
        header_color=header_color,
    )


if __name__ == "__main__":
    main()
