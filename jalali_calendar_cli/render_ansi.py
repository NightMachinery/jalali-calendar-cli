##
#: Terminal (ANSI) formatter for a `MonthModel`.
##
import datetime
import re
from dataclasses import dataclass, field
from typing import Dict, Optional

import colorama
from colorama import Style

from .model import MonthModel

# init(autoreset=False)
#: This actually causes 'print' to be monkey-patched to not print ANSI codes when piping.


#: Color presets for different themes.
#: `back` marks the colors that are drawn as a background.
COLOR_PRESETS = {
    "light": {
        "weekend": {"name": "LIGHTMAGENTA_EX", "true": (85, 26, 139)},
        "holiday": {"name": "LIGHTRED_EX", "true": (230, 69, 0)},
        "footnote": {"name": "LIGHTBLACK_EX", "true": (170, 170, 170)},
        "header": {"name": "BLACK", "true": (50, 50, 50)},
        # "today": {"name": "CYAN", "true": (50, 230, 230)},
        "today": {"name": "CYAN", "true": (255, 255, 255)},
        #: both sides are free on this day
        "shared": {"name": "YELLOW", "true": (184, 134, 11)},
        "secondary_holiday": {"name": "CYAN", "true": (150, 215, 232)},
        "secondary_weekend": {"name": "LIGHTBLACK_EX", "true": (222, 241, 247)},
    },
    "dark": {
        "weekend": {"name": "LIGHTMAGENTA_EX", "true": (255, 0, 255)},
        "holiday": {"name": "LIGHTRED_EX", "true": (255, 0, 0)},
        "footnote": {"name": "LIGHTBLACK_EX", "true": (128, 128, 128)},
        "header": {"name": "WHITE", "true": (255, 255, 255)},
        # "today": {"name": "CYAN", "true": (30, 200, 200)},
        "today": {"name": "CYAN", "true": (255, 120, 0)},
        # "today": {"name": "WHITE", "true": (255, 255, 255)},
        "shared": {"name": "LIGHTYELLOW_EX", "true": (255, 205, 40)},
        "secondary_holiday": {"name": "CYAN", "true": (0, 98, 120)},
        "secondary_weekend": {"name": "LIGHTBLACK_EX", "true": (0, 44, 54)},
    },
}

COLOR_KEYS = tuple(COLOR_PRESETS["light"].keys())
BACKGROUND_KEYS = frozenset({"today", "secondary_holiday", "secondary_weekend"})

UNDERLINE = "\x1b[4m"

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


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


def generate_true_color_code(red: int, green: int, blue: int, back=False) -> str:
    """
    Generates ANSI escape code for 24-bit true colors.

    Args:
        red (int): The intensity of the red color component (0-255).
        green (int): The intensity of the green color component (0-255).
        blue (int): The intensity of the blue color component (0-255).

    Returns:
        str: The ANSI escape code for the specified true color.

    """

    if back:
        code = 48
    else:
        code = 38

    #: @seeAlso `wh colorfg colorbg`
    escape_code = f"\x1b[{code};2;{red};{green};{blue}m"
    return escape_code


@dataclass
class DisplayOptions:
    color: bool = False
    true_color: bool = False
    color_preset: str = "light"
    #: {color_key: {"name": ..., "true": (r, g, b)}}, overriding the preset
    color_overrides: Dict[str, dict] = field(default_factory=dict)
    indentation: int = 5
    line_prefix: str = " "
    footnotes: bool = True


def resolve_palette(opts: DisplayOptions) -> Dict[str, str]:
    """Returns the ANSI code for every color key, plus `bold` and `reset`."""
    if not opts.color:
        palette = {key: "" for key in COLOR_KEYS}
        palette["bold"] = ""
        palette["reset"] = ""
        return palette

    preset = COLOR_PRESETS[opts.color_preset]
    palette = dict()
    for key in COLOR_KEYS:
        spec = opts.color_overrides.get(key) or preset[key]
        back = key in BACKGROUND_KEYS
        if opts.true_color:
            palette[key] = generate_true_color_code(*spec["true"], back=back)
        else:
            palette[key] = getattr(colorama.Back if back else colorama.Fore, spec["name"])

    palette["bold"] = Style.BRIGHT
    palette["reset"] = Style.RESET_ALL
    return palette


def render_grid(
    model: MonthModel,
    opts: DisplayOptions,
    today: Optional[datetime.date] = None,
):
    """Returns `(calendar, footnotes)` as strings, without the line prefix."""
    indentation = opts.indentation
    assert indentation >= 3

    p = resolve_palette(opts)
    bold_ansi = p["bold"]
    reset_color = p["reset"]

    header_indentation_len = indentation - 3
    blank1 = " " * indentation
    calendar = [blank1 * model.first_column]

    last_indentation_debt = header_indentation_len
    num_days = len(model.cells)
    for cell in model.cells:
        day = cell.day
        day_str = str(day)
        day_str = day_str.rjust(indentation - last_indentation_debt)
        last_indentation_debt = 0

        #: The highlight is a background on the last three characters of the cell.
        #: With two holiday sets the background belongs to the second set, so today is
        #: marked with bold and underline instead, keeping that background.
        is_today = today is not None and cell.date == today
        if is_today and not cell.overlay:
            highlight = f"{bold_ansi}{p['today']}"
        elif cell.secondary_holiday:
            highlight = p["secondary_holiday"]
        elif cell.secondary_weekend:
            highlight = p["secondary_weekend"]
        else:
            highlight = ""
        underline = is_today and cell.overlay and opts.color

        if highlight or underline:
            # bg_len = (day_str_orig_len + 1)
            bg_len = 3
            head, tail = day_str[:-bg_len], day_str[-bg_len:]
            if underline:
                #: only under the digits, not the padding before them
                digits = len(str(day))
                tail = f"{tail[:-digits]}{bold_ansi}{UNDERLINE}{tail[-digits:]}"

            day_str = f"{head}{highlight}{tail}{reset_color}"

        if cell.both_free:
            day_str = f"{bold_ansi}{p['shared']}{day_str}{reset_color}"
        elif cell.primary_holiday:
            day_str = f"{bold_ansi}{p['holiday']}{day_str}{reset_color}"
        elif cell.primary_weekend:
            day_str = f"{p['weekend']}{day_str}{reset_color}"

        calendar.append(day_str)

        if cell.column == 6 and day != num_days:
            calendar.append("\n")
            last_indentation_debt = header_indentation_len

    label_sep = " " * header_indentation_len
    headers_weekdays_plain = label_sep.join(label.text for label in model.weekday_labels)
    headers_weekdays = label_sep.join(
        f"{p['secondary_weekend']}{label.text}{reset_color}{bold_ansi}"
        if label.secondary_weekend and p["secondary_weekend"]
        else label.text
        for label in model.weekday_labels
    )
    width = len(headers_weekdays_plain)

    headers = ""
    headers += f"{bold_ansi}{p['header']}{center_justify(model.title, width)}{reset_color}\n"
    if model.subtitle:
        headers += f"{p['footnote']}{center_justify(model.subtitle, width)}{reset_color}\n"
    headers += f"{bold_ansi}{headers_weekdays}{reset_color}"

    footnotes = "\n".join(format_footnote(f) for f in model.footnotes)

    return f"{headers}\n{''.join(calendar)}", footnotes


def format_footnote(footnote) -> str:
    line = f"{footnote.day:2d}: "
    if footnote.tag:
        line += f"{footnote.tag:<4} "
    line += footnote.name
    if footnote.note:
        line += f" ({footnote.note})"
    return line


def format_month(
    model: MonthModel,
    opts: DisplayOptions,
    today: Optional[datetime.date] = None,
) -> str:
    """The full month as printed by `jcal`, including the trailing newline."""
    calendar, footnotes = render_grid(model, opts, today=today)
    line_prefix = opts.line_prefix
    out = prefix_lines(calendar, prefix=line_prefix) + "\n"

    if opts.footnotes and model.footnotes:
        footnotes = prefix_lines(footnotes, prefix=f"{line_prefix}  ")

        out += f"\n{line_prefix}Holidays:\n"
        out += footnotes + "\n"

    return out
