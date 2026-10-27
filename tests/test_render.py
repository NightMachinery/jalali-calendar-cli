import contextlib
import io
import os
import shutil

from jalali_calendar_cli.calendars import JALALI
from jalali_calendar_cli.commands import jcal_iran_lmu
from jalali_calendar_cli.jalali_calendar import main
from jalali_calendar_cli.model import build_month
from jalali_calendar_cli.render_ansi import DisplayOptions, format_month, format_months, strip_ansi
from jalali_calendar_cli.sources.iran import IranSource


def run_main(argv, command=main):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        command(argv)
    return out.getvalue()


def test_main_uses_its_argument_list():
    out = run_main(["7", "1402", "--color", "never"])
    assert "1402 Mehr" in out


def test_today_color_override_is_applied():
    model = build_month(JALALI, IranSource(), None, 1402, 7)
    today = model.cells[9].date  # 10 Mehr
    opts = DisplayOptions(
        color=True,
        true_color=True,
        color_overrides={"today": {"true": (1, 2, 3)}},
    )
    out = format_month(model, opts, today=today)
    assert "\x1b[48;2;1;2;3m 10" in out


def test_month_without_holidays_has_no_empty_holidays_block(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("{}")
    model = build_month(JALALI, IranSource(holidays_json_path=str(empty), fallback=False), None, 1402, 7)
    out = format_month(model, DisplayOptions())
    assert "Holidays:" not in out


def test_next_month_is_shown_by_default():
    title = run_main(["7", "1402", "--color", "never"]).splitlines()[0]
    assert "1402 Mehr" in title and "1402 Aban" in title


def test_next_month_can_be_turned_off():
    out = run_main(["7", "1402", "--color", "never", "--next-month", "never"])
    model = build_month(JALALI, IranSource(), None, 1402, 7)
    assert out == format_month(model, DisplayOptions(line_prefix=" "))


def test_next_month_crosses_the_year():
    title = run_main(["12", "1405", "--color", "never"]).splitlines()[0]
    assert "1405 Esfand" in title and "1406 Farvardin" in title


def test_each_month_has_its_holidays_under_it():
    lines = run_main(["12", "1402", "--color", "never"]).splitlines()
    second_month = lines[1].index(" Sat", 1)
    header = next(line for line in lines if "Holidays:" in line)
    assert header.index(" Holidays:", 1) == second_month
    row = lines[lines.index(header) + 1]
    assert row[:second_month].rstrip() == "    6: Birthday of Imam Mahdi"
    assert row[second_month:] == "    1: Norooz Start"


def test_long_holiday_names_wrap_within_their_month():
    out = run_main(["7", "1402", "--color", "never"])
    width = len(out.splitlines()[1])
    assert max(len(line) for line in out.splitlines()) <= width
    #: the rest of a name goes under its start
    assert "    2: Martyrdom of Imam Hassan\n       Askari and Start of Imamate\n" in out


def test_notes_are_not_split():
    lines = run_main(["3", "1405", "--color", "never"], command=jcal_iran_lmu).splitlines()
    left = [line[: lines[2].index(" Sat", 1)].rstrip() for line in lines]
    index = left.index("    4: LMU  Pentecost Monday")
    assert left[index + 1] == "            (25 May)"


def test_colored_months_side_by_side_match_the_plain_layout():
    colored = run_main(["12", "1402", "--color", "always", "--true-color"])
    plain = run_main(["12", "1402", "--color", "never"])
    #: a colored title keeps its centering spaces inside the color codes
    assert [line.rstrip() for line in strip_ansi(colored).splitlines()] == plain.splitlines()


def test_months_go_one_below_the_other_on_a_narrow_terminal():
    models = [build_month(JALALI, IranSource(), None, 1402, month) for month in (7, 8)]
    wide = format_months(models, DisplayOptions(), columns=80).splitlines()
    assert "1402 Mehr" in wide[0] and "1402 Aban" in wide[0]
    #: each with its own holiday list, as when shown alone
    narrow = format_months(models, DisplayOptions(), columns=40)
    assert narrow == "\n".join(format_month(model, DisplayOptions()) for model in models)


class Terminal(io.StringIO):
    def isatty(self):
        return True


def run_on_terminal(argv, columns, monkeypatch):
    monkeypatch.setattr(shutil, "get_terminal_size", lambda: os.terminal_size((columns, 24)))
    out = Terminal()
    with contextlib.redirect_stdout(out):
        main(argv)
    return out.getvalue()


def test_next_month_auto_needs_room_for_both(monkeypatch):
    argv = ["7", "1402", "--color", "never"]
    wide = run_on_terminal(argv, 100, monkeypatch).splitlines()[0]
    assert "1402 Mehr" in wide and "1402 Aban" in wide
    #: two months side by side take 71 columns
    narrow = run_on_terminal(argv, 70, monkeypatch)
    assert narrow == run_main([*argv, "--next-month", "never"])


def test_next_month_always_goes_below_when_there_is_no_room(monkeypatch):
    out = run_on_terminal(["7", "1402", "--color", "never", "--next-month", "always"], 70, monkeypatch)
    titles = [line.strip() for line in out.splitlines() if line.strip().startswith("1402")]
    assert titles == ["1402 Mehr", "1402 Aban"]
