import contextlib
import datetime
import io

from jalali_calendar_cli.calendars import GREGORIAN, JALALI
from jalali_calendar_cli.commands import gcal_lmu_iran, gcal_lmu_iran_all, jcal_iran_lmu
from jalali_calendar_cli.model import build_month
from jalali_calendar_cli.sources.iran import IranSource
from jalali_calendar_cli.sources.lmu import LmuSource

SECONDARY_HOLIDAY_BG = "\x1b[48;2;150;215;232m"
SECONDARY_WEEKEND_BG = "\x1b[48;2;222;241;247m"
SHARED_FG = "\x1b[38;2;184;134;11m"


def run(command, argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        command(argv)
    return out.getvalue()


def cell(model, day):
    return model.cells[day - 1]


def test_june_2026_footnotes():
    out = run(gcal_lmu_iran, ["6", "2026", "--color", "never"])
    assert out.splitlines()[:2] == [
        "             2026 June            ",
        "         Khordad–Tir 1405         ",
    ]
    assert out.split(" Holidays:\n")[1] == (
        "    4: LMU  Corpus Christi\n"
        "    4: IR   Eid Saeed Ghadir Khumm - Demise of Imam Khomeini (14 Khordad)\n"
        "    5: IR   Revolt of 15 Khordad (15 Khordad)\n"
        "   24: IR   Tasu'a Hosseini (3 Tir)\n"
        "   25: IR   Ashura Hosseini (4 Tir)\n"
    )


def test_june_2026_colors():
    lines = run(gcal_lmu_iran, ["6", "2026", "--color", "always", "--true-color"]).splitlines()
    #: header: the Iranian weekend is tinted
    assert f"{SECONDARY_WEEKEND_BG}Thu" in lines[2]
    assert f"{SECONDARY_WEEKEND_BG}Fri" in lines[2]
    #: Jun 4: both off, gold text on the secondary-holiday background
    assert f"{SHARED_FG}  {SECONDARY_HOLIDAY_BG}  4" in lines[3]
    #: Jun 11: a plain Thursday, the faint weekend tint
    assert f"{SECONDARY_WEEKEND_BG} 11" in lines[4]
    #: Jun 24: an Iranian holiday on a Wednesday, background only
    assert f"  {SECONDARY_HOLIDAY_BG} 24" in lines[6]


def test_both_free_through_weekends():
    model = build_month(GREGORIAN, LmuSource(), IranSource(), 2026, 1)
    #: New Year's Day 2026 is a Thursday, part of the Iranian weekend
    assert cell(model, 1).both_free
    model = build_month(GREGORIAN, LmuSource(), IranSource(), 2026, 3)
    #: 1 Farvardin 1405 (Nowruz) is a Saturday
    assert cell(model, 21).both_free
    #: a plain Saturday is free only for LMU
    assert not cell(model, 14).both_free


def test_single_source_view_has_no_shared_days():
    model = build_month(GREGORIAN, LmuSource(), None, 2026, 6)
    assert not any(c.both_free for c in model.cells)
    assert all(f.tag is None for f in model.footnotes)


def test_mirror_views_agree():
    def facts(calendar, primary, secondary, year):
        out = set()
        for month in range(1, 13):
            model = build_month(calendar, primary, secondary, year, month)
            for f in model.footnotes:
                out.add((calendar.to_gregorian(year, month, f.day), f.tag, f.name))
        return out

    lmu, iran = LmuSource(), IranSource()
    start, end = datetime.date(2026, 3, 21), datetime.date(2027, 3, 20)  # Jalali 1405
    gregorian = {
        fact
        for year in (2026, 2027)
        for fact in facts(GREGORIAN, lmu, iran, year)
        if start <= fact[0] <= end
    }
    assert gregorian == facts(JALALI, iran, lmu, 1405)


def test_jalali_overlay_notes_use_gregorian_dates():
    out = run(jcal_iran_lmu, ["3", "1405", "--color", "never"])
    assert "   14: LMU  Corpus Christi (4 Jun)" in out
    assert out.splitlines()[1].strip() == "May–June 2026"


def test_today_keeps_the_secondary_background_in_overlay_views():
    from jalali_calendar_cli.render_ansi import DisplayOptions, format_month

    model = build_month(GREGORIAN, LmuSource(), IranSource(), 2026, 6)
    opts = DisplayOptions(color=True, true_color=True)
    #: Jun 11 is a Thursday: the faint Iranian-weekend tint, plus bold and underline for today
    out = format_month(model, opts, today=datetime.date(2026, 6, 11))
    #: the underline starts at the digits, not at the padding before them
    assert f"{SECONDARY_WEEKEND_BG} \x1b[1m\x1b[4m11" in out
    #: today's own background is not used
    assert "\x1b[48;2;255;255;255m" not in out


def test_secondary_weekend_columns_are_unbroken():
    from jalali_calendar_cli.render_ansi import DisplayOptions, format_month, strip_ansi

    #: November 2026 starts on a Sunday and ends on a Monday, so its first and last rows
    #: have empty Thursday and Friday cells, which are tinted too.
    model = build_month(GREGORIAN, LmuSource(), IranSource(), 2026, 11)
    out = format_month(model, DisplayOptions(color=True, true_color=True), today=None)
    lines = out.split("\n")
    first_row, last_row = lines[3], lines[8]
    assert first_row.count(SECONDARY_WEEKEND_BG) == 2
    assert last_row.count(SECONDARY_WEEKEND_BG) == 2
    #: the tint does not move anything
    plain = format_month(model, DisplayOptions(), today=None).split("\n")
    assert strip_ansi(first_row) == plain[3]
    assert strip_ansi(last_row).rstrip() == plain[8]

