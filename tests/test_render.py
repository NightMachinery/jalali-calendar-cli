import contextlib
import io

from jalali_calendar_cli.calendars import JALALI
from jalali_calendar_cli.jalali_calendar import main
from jalali_calendar_cli.model import build_month
from jalali_calendar_cli.render_ansi import DisplayOptions, format_month
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
