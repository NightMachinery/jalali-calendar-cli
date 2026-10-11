##
#: HTML formatter for a `MonthModel`: the same decisions as the terminal formatter, drawn
#: as a table whose cells carry one CSS class per role.
#:
#: - `ph`: primary holiday, `pw`: primary weekend
#: - `sh`: secondary holiday, `sw`: secondary weekend
#: - `both`: both sides are free
#:
#: The weekend tint (`sw`) is the cell's own background, so that a weekend column is one
#: unbroken band; the other backgrounds go on the number's box inside the cell, on top.
##
import datetime
import json
from html import escape

from .calendars import GREGORIAN, JALALI
from .model import MonthModel


def cell_classes(cell) -> str:
    classes = []
    if cell.primary_holiday:
        classes.append("ph")
    elif cell.primary_weekend:
        classes.append("pw")
    if cell.secondary_holiday:
        classes.append("sh")
    if cell.secondary_weekend:
        classes.append("sw")
    if cell.both_free:
        classes.append("both")
    return " ".join(classes)


def label_classes(label) -> str:
    classes = []
    if label.primary_weekend:
        classes.append("pw")
    if label.secondary_weekend:
        classes.append("sw")
    return " ".join(classes)


def _class_attr(classes: str) -> str:
    return f' class="{classes}"' if classes else ""


def other_calendar_segments(model: MonthModel, calendar) -> list:
    """Where each month of the other calendar starts in this month's grid.

    `[[grid_day, other_day, other_month_name, other_year], ...]`, one entry for the first
    day and one for each day that is a 1st in the other calendar. The page's tooltips
    derive any day's other date from these by adding days, without converting calendars.
    """
    other = GREGORIAN if calendar is JALALI else JALALI
    segments = []
    for cell in model.cells:
        year, month, day = other.from_gregorian(cell.date)
        if not segments or day == 1:
            segments.append([cell.day, day, other.month_name(month), year])
    return segments


def cell_tip(model: MonthModel, cell) -> str:
    """The data of a day's tooltip beyond its dates: its holidays, and whether both sides
    are free. Empty for a day with neither."""
    holidays = [
        [footnote.tag or "", footnote.name, int(footnote.secondary)]
        for footnote in model.footnotes
        if footnote.day == cell.day
    ]
    if not holidays and not cell.both_free:
        return ""
    data = {"h": holidays}
    if cell.both_free:
        data["b"] = 1
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def month_html(model: MonthModel, view_id: str, calendar) -> str:
    """`calendar` is the grid calendar."""
    start: datetime.date = model.cells[0].date
    end: datetime.date = model.cells[-1].date
    other_dates = json.dumps(other_calendar_segments(model, calendar), separators=(",", ":"))
    out = [
        f'<section class="month" data-view="{view_id}" data-year="{model.year}"'
        f' data-month="{model.month}" data-start="{start.isoformat()}" data-end="{end.isoformat()}"'
        f' data-label="{escape(calendar.month_name(model.month))} {model.year}"'
        f' data-other="{escape(other_dates)}" hidden>'
    ]
    out.append(f'<h2 class="title">{escape(model.title)}</h2>')
    if model.subtitle:
        out.append(f'<p class="subtitle">{escape(model.subtitle)}</p>')

    out.append('<table class="grid"><thead><tr>')
    for label in model.weekday_labels:
        out.append(f"<th{_class_attr(label_classes(label))}>{escape(label.text)}</th>")
    out.append("</tr></thead><tbody><tr>")

    #: empty cells in the second set's weekend columns are tinted too, as in the terminal
    def blank(column):
        return '<td class="sw"></td>' if model.weekday_labels[column].secondary_weekend else "<td></td>"

    out.extend(blank(column) for column in range(model.first_column))
    for cell in model.cells:
        tip = cell_tip(model, cell)
        tip_attr = f' data-tip="{escape(tip)}"' if tip else ""
        out.append(f"<td{_class_attr(cell_classes(cell))}{tip_attr}><span>{cell.day}</span></td>")
        if cell.column == 6 and cell is not model.cells[-1]:
            out.append("</tr><tr>")
    last_column = model.cells[-1].column
    out.extend(blank(column) for column in range(last_column + 1, 7))
    out.append("</tr></tbody></table>")

    if model.footnotes:
        out.append('<ul class="notes">')
        for footnote in model.footnotes:
            role = "secondary" if footnote.secondary else "primary"
            item = f'<li class="{role}"><span class="day">{footnote.day}</span>'
            if footnote.tag:
                item += f'<span class="tag">{escape(footnote.tag)}</span>'
            item += f'<span class="name">{escape(footnote.name)}</span>'
            if footnote.note:
                item += f' <span class="native">{escape(footnote.note)}</span>'
            item += "</li>"
            out.append(item)
        out.append("</ul>")

    out.append("</section>")
    return "".join(out)
