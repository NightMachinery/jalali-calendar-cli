##
# * @todo
# ** Make the true color customizable.
# *** Add a preset color theme for dark themes
##
import pathlib
from typing import List
import sys
import jdatetime
import datetime
import json
import os
import argparse
from colorama import Fore, Style, init

try:
    from icecream import ic, colorize as ic_colorize

    ic.configureOutput(outputFunction=lambda s: print(ic_colorize(s)))
except ImportError:
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)


init(autoreset=False)


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

    blue_start = (
        generate_true_color_code(85, 26, 139)
        if true_color
        else (Fore.BLUE if color else "")
    )
    red_start = (
        generate_true_color_code(230, 69, 0)
        if true_color
        else (Fore.RED if color else "")
    )
    gray_start = (
        generate_true_color_code(170, 170, 170)
        if true_color
        else (Fore.LIGHTBLACK_EX if color else "")
    )
    black_start = (
        generate_true_color_code(50, 50, 50)
        if true_color
        else (Fore.WHITE if color else "")
        #: White themes should have set WHITE to the color black, and dark themes to white.
    )
    bold_start = Style.BRIGHT if color else ""
    reset_color = Style.RESET_ALL if color else ""

    last_indentation_debt = header_indentation_len
    for day in range(1, num_days + 1):
        weekday = (day + first_day_of_month) % 7
        day_str = str(day)
        day_str = day_str.rjust(indentation - last_indentation_debt)
        last_indentation_debt = 0

        if day in holidays:
            footnotes.append(f"{day}: {holidays[day]}")

            if (
                False
            ):  #: @cruft no need to use footnotes when the days can act as indices already
                footnotes.append(f"{len(footnotes)+1}: {holidays[day]}")
                footnote_num_str = str(len(footnotes))
                if unicode_p:
                    footnote_num_str = footnote_num_str.translate(superscript_map)
                else:
                    footnote_num_str = f"[{footnote_num_str}]"

                last_indentation_debt += len(footnote_num_str)
            else:
                footnote_num_str = ""

            day_str = f"{bold_start}{red_start}{day_str}{reset_color}"
            if footnote_num_str:
                day_str += f"{gray_start}{footnote_num_str}{reset_color}"

        elif weekday == 0:
            day_str = f"{blue_start}{day_str}{reset_color}"

        # ic(indentation, day_str, day_str.rjust(indentation))
        calendar.append(day_str)

        if weekday == 0:
            calendar.append("\n")
            last_indentation_debt = header_indentation_len

    headers_weekdays = (" " * header_indentation_len).join(weekdays)

    headers = ""
    year_month_str = f"{year} {jmonth_name(month)}"
    headers += f"{bold_start}{black_start}{center_justify(year_month_str, len(headers_weekdays))}{reset_color}\n"
    headers += f"{bold_start}{headers_weekdays}{reset_color}"

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

    default_holiday_data_json_path = (
        os.getenv("JALALI_HOLIDAYS_JSON_PATH")
        or str(pathlib.Path(__file__).parent / "holidays.json")
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
        help="Month in Jalali calendar",
    )
    parser.add_argument(
        "year",
        type=int,
        nargs="?",
        default=now_jalali.year,
        help="Year in Jalali calendar",
    )
    ##
    # parser.add_argument("month", type=int, help="Month in Jalali calendar")
    # parser.add_argument("year", type=int, help="Year in Jalali calendar")
    ##

    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="Colorize the output",
    )

    # parser.add_argument(
    #     "--unicode",
    #     action=argparse.BooleanOptionalAction,
    #     default=True,
    #     help="Enable Unicode superscript for footnote numbers",
    # )

    parser.add_argument(
        "--true-color",
        action=argparse.BooleanOptionalAction,
        # default=True,
        default=False,  #: to make the default compatible with dark themes
        help="Enable true color support for output",
    )
    parser.add_argument(
        "--footnotes",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show footnotes in the output",
    )
    parser.add_argument(
        "--indentation",
        type=int,
        default=5,
        help="Number of spaces for indentation (default: 5)",
    )
    parser.add_argument(
        "--holidays-json-path",
        type=str,
        default=default_holiday_data_json_path,
        help="Path to JSON file containing holiday data",
    )

    args = parser.parse_args()

    color = args.color == "always" or (args.color == "auto" and sys.stdout.isatty())

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
        footnotes_p=args.footnotes,
        holidays_data=holidays_data,
    )


if __name__ == "__main__":
    main()
