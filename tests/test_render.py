import contextlib
import io

from jalali_calendar_cli.calendars import JALALI
from jalali_calendar_cli.jalali_calendar import main
from jalali_calendar_cli.model import build_month
from jalali_calendar_cli.render_ansi import DisplayOptions, format_month, format_months, strip_ansi
from jalali_calendar_cli.sources.iran import IranSource


def run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        main(argv)
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
    out = run_main(["7", "1402", "--color", "never"])
    title = out.splitlines()[0]
    assert "1402 Mehr" in title and "1402 Aban" in title
    #: one holiday list, each entry led by its month (Aban 1402 has none)
    assert out.split(" Holidays:\n")[1].startswith("   Meh  2: ")
    assert "   Aba " not in out


def test_next_month_can_be_turned_off():
    out = run_main(["7", "1402", "--color", "never", "--no-next-month"])
    model = build_month(JALALI, IranSource(), None, 1402, 7)
    assert out == format_month(model, DisplayOptions(line_prefix=" "))


def test_next_month_crosses_the_year():
    title = run_main(["12", "1405", "--color", "never"]).splitlines()[0]
    assert "1405 Esfand" in title and "1406 Farvardin" in title


def test_colored_months_side_by_side_are_aligned():
    out = run_main(["12", "1402", "--color", "always", "--true-color"])
    grid = out.split("Holidays:")[0]
    widths = {len(strip_ansi(line)) for line in grid.splitlines() if line.strip()}
    assert len(widths) == 1


def test_months_go_one_below_the_other_on_a_narrow_terminal():
    models = [build_month(JALALI, IranSource(), None, 1402, month) for month in (7, 8)]
    wide = format_months(models, DisplayOptions(), JALALI, columns=80).splitlines()
    assert "1402 Mehr" in wide[0] and "1402 Aban" in wide[0]
    #: the holiday names are free to wrap, as they do for one month
    narrow = format_months(models, DisplayOptions(), JALALI, columns=40).split("Holidays:")[0]
    assert max(len(line) for line in narrow.splitlines()) <= 40
    titles = [line.strip() for line in narrow.splitlines() if line.strip().startswith("1402")]
    assert titles == ["1402 Mehr", "1402 Aban"]
