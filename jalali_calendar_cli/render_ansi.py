##
#: Terminal (ANSI) formatter for a `MonthModel`.
##
import datetime
import re
import textwrap
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

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
        #: the background of a day on which both sides are free
        "shared": {"name": "YELLOW", "true": (247, 212, 125)},
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
        "shared": {"name": "YELLOW", "true": (110, 82, 0)},
        "secondary_holiday": {"name": "CYAN", "true": (0, 98, 120)},
        "secondary_weekend": {"name": "LIGHTBLACK_EX", "true": (0, 44, 54)},
    },
}

COLOR_KEYS = tuple(COLOR_PRESETS["light"].keys())
BACKGROUND_KEYS = frozenset({"today", "shared", "secondary_holiday", "secondary_weekend"})

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
    #: put the other calendar's span on the title line, when it fits
    one_line_title: bool = False


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

    #: Columns of the second set's weekend are tinted from the header down, including
    #: the empty cells before the first and after the last day, so they read as columns.
    tinted_columns = (
        {col for col, label in enumerate(model.weekday_labels) if label.secondary_weekend}
        if p["secondary_weekend"]
        else set()
    )

    def blank_cell(width, column):
        if column in tinted_columns:
            return f"{' ' * (width - 3)}{p['secondary_weekend']}   {reset_color}"
        return " " * width

    #: The first column is 3 wide, the others `indentation` (separator plus 3); the
    #: separator before the first day is added after the blanks.
    leading = [blank_cell(3 if col == 0 else indentation, col) for col in range(model.first_column)]
    if model.first_column:
        leading.append(" " * header_indentation_len)
    calendar = ["".join(leading)]

    last_indentation_debt = header_indentation_len
    num_days = len(model.cells)
    for cell in model.cells:
        day = cell.day
        day_str = str(day)
        day_str = day_str.rjust(indentation - last_indentation_debt)
        last_indentation_debt = 0

        #: The highlight is a background on the last three characters of the cell.
        #: With two holiday sets the background belongs to the second set, or is gold when
        #: both sides are free, so today is marked with bold and underline instead.
        is_today = today is not None and cell.date == today
        if is_today and not cell.overlay:
            highlight = f"{bold_ansi}{p['today']}"
        elif cell.both_free:
            highlight = p["shared"]
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

        if cell.primary_holiday:
            day_str = f"{bold_ansi}{p['holiday']}{day_str}{reset_color}"
        elif cell.primary_weekend:
            day_str = f"{p['weekend']}{day_str}{reset_color}"

        calendar.append(day_str)

        if cell.column == 6 and day != num_days:
            calendar.append("\n")
            last_indentation_debt = header_indentation_len

    #: the tinted columns after the last day; nothing past the last of them, so plain
    #: output keeps no trailing spaces
    last_column = model.cells[-1].column
    trailing = [col for col in tinted_columns if col > last_column]
    if trailing:
        calendar.extend(blank_cell(indentation, col) for col in range(last_column + 1, max(trailing) + 1))

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
    one_line = f"{model.title} · {model.short_subtitle}" if model.short_subtitle else None
    if opts.one_line_title and one_line and len(one_line) <= width:
        #: centered as a whole, the span in the subtitle's color
        line = center_justify(one_line, width)
        pad = line[: len(line) - len(line.lstrip(" "))]
        headers += (
            f"{pad}{bold_ansi}{p['header']}{model.title}{reset_color}"
            f"{p['footnote']} · {model.short_subtitle}{reset_color}{line[len(pad) + len(one_line):]}\n"
        )
    else:
        headers += f"{bold_ansi}{p['header']}{center_justify(model.title, width)}{reset_color}\n"
        if model.subtitle:
            headers += f"{p['footnote']}{center_justify(model.subtitle, width)}{reset_color}\n"
    headers += f"{bold_ansi}{headers_weekdays}{reset_color}"

    footnotes = "\n".join(format_footnote(f) for f in model.footnotes)

    return f"{headers}\n{''.join(calendar)}", footnotes


def footnote_lead(footnote) -> str:
    """What comes before a footnote's name: its day, and its tag when there is one."""
    lead = f"{footnote.day:2d}: "
    if footnote.tag:
        lead += f"{footnote.tag:<4} "
    return lead


def footnote_text(footnote) -> str:
    """A footnote's name, and its note when there is one."""
    if footnote.note:
        return f"{footnote.name} ({footnote.note})"
    return footnote.name


def format_footnote(footnote) -> str:
    return footnote_lead(footnote) + footnote_text(footnote)


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


def month_lines(model: MonthModel, opts: DisplayOptions, today: Optional[datetime.date] = None) -> List[str]:
    """`format_month` as a list of lines, without the trailing newline."""
    return format_month(model, opts, today=today).rstrip("\n").split("\n")


def side_by_side(blocks: List[List[str]], gap: int, width: Optional[int] = None) -> List[str]:
    """Blocks of lines next to each other, `gap` spaces apart, each padded to `width`
    (default: the widest line)."""
    if width is None:
        width = max(len(strip_ansi(line)) for lines in blocks for line in lines)
    height = max(len(lines) for lines in blocks)
    out = []
    for i in range(height):
        cells = []
        for lines in blocks:
            line = lines[i] if i < len(lines) else ""
            cells.append(line + " " * (width - len(strip_ansi(line))))
        out.append((" " * gap).join(cells))
    return out


def month_footnotes(models: List[MonthModel], calendar, line_prefix: str) -> List[str]:
    """The footnotes of several months in one list, each led by its month's abbreviated name."""
    return [
        f"{line_prefix}  {calendar.month_name(model.month)[:3]} {format_footnote(footnote)}"
        for model in models
        for footnote in model.footnotes
    ]


def footnote_column(model: MonthModel, line_prefix: str, width: int) -> List[str]:
    """A month's holiday list, to go under it beside another month's: the names are
    wrapped to keep it within `width`."""
    if not model.footnotes:
        return []
    lines = [f"{line_prefix}Holidays:"]
    for footnote in model.footnotes:
        lead = f"{line_prefix}  {footnote_lead(footnote)}"
        #: a note such as "(25 May)" is not split; `textwrap` does not break at no-break spaces
        text = footnote.name
        if footnote.note:
            text += " (" + footnote.note.replace(" ", "\xa0") + ")"
        parts = textwrap.wrap(text, max(width - len(lead), 10), break_long_words=False)
        parts = [part.replace("\xa0", " ") for part in parts]
        lines.append(lead + parts[0])
        lines.extend(" " * len(lead) + part for part in parts[1:])
    return lines


#: spaces between months side by side, after each month's own line prefix
MONTHS_GAP = 3


def fits_side_by_side(models: List[MonthModel], opts: DisplayOptions, columns: Optional[int], gap: int = MONTHS_GAP) -> bool:
    """Whether the months fit side by side in `columns`; `None` means there is no limit.
    The holiday lists always fit, since their names wrap to the month's width."""
    if columns is None:
        return True
    blocks = [month_lines(model, replace(opts, footnotes=False)) for model in models]
    width = max(len(strip_ansi(line)) for lines in blocks for line in lines)
    return width * len(blocks) + gap * (len(blocks) - 1) <= columns


def format_months(
    models: List[MonthModel],
    opts: DisplayOptions,
    today: Optional[datetime.date] = None,
    gap: int = MONTHS_GAP,
    columns: Optional[int] = None,
) -> str:
    """Consecutive months side by side, each with its holiday list under it.

    When `columns` is given and they do not fit in it, they go one below the other.
    """
    if len(models) == 1:
        return format_month(models[0], opts, today=today)
    if not fits_side_by_side(models, opts, columns, gap):
        return "\n".join(format_month(model, opts, today=today) for model in models)

    blocks = [month_lines(model, replace(opts, footnotes=False), today) for model in models]
    width = max(len(strip_ansi(line)) for lines in blocks for line in lines)

    lines = side_by_side(blocks, gap, width)
    footnotes = [footnote_column(model, opts.line_prefix, width) for model in models] if opts.footnotes else []
    if any(footnotes):
        lines += [""] + side_by_side(footnotes, gap, width)

    #: the padding of the last column is not needed; a tinted cell ends in a reset code, so it stays
    return "\n".join(line.rstrip(" ") for line in lines) + "\n"
