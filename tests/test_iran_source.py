import subprocess
import sys

from jalali_calendar_cli.calendars import JALALI
from jalali_calendar_cli.sources.iran import IranSource


def jalali_dates(events):
    return {JALALI.from_gregorian(date): name for date, name in events.items()}


def year_events(source, year):
    start = JALALI.to_gregorian(year, 1, 1)
    end = JALALI.to_gregorian(year, 12, 29)
    return jalali_dates(source.events(start, end))


def test_covered_year_comes_from_json():
    events = year_events(IranSource(), 1405)
    #: the official calendar's date, where the computed one says 1405-12-10 "(estimated)"
    assert events[(1405, 12, 9)] == "Martyrdom of Imam Ali"
    assert not any("estimated" in name for name in events.values())


def test_uncovered_year_falls_back_to_holidays_package():
    events = year_events(IranSource(), 1410)
    assert "Nowruz" in events[(1410, 1, 1)]
    assert any("(estimated)" in name for name in events.values())


def test_fallback_can_be_disabled():
    assert year_events(IranSource(fallback=False), 1410) == {}


def test_jcal_for_covered_year_does_not_import_holidays():
    code = (
        "import sys, io, contextlib\n"
        "from jalali_calendar_cli.jalali_calendar import main\n"
        "with contextlib.redirect_stdout(io.StringIO()): main(['7', '1405', '--color', 'never'])\n"
        "print('holidays' in sys.modules)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True).stdout
    assert out.strip() == "False"
