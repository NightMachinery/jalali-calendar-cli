import contextlib
import datetime
import io

from jalali_calendar_cli.commands import gcal, gcal_all, gcal_lmu, gcal_lmu_all, gcal_lmu_iran_all
from jalali_calendar_cli.sources.lmu import LmuSource

#: Bavarian public holidays for 2026 (Munich, so with Assumption Day). Cross-checked on
#: 2026-10-11 against https://ics.tools/Feiertage/bayern.ics for 2026 to 2028.
BAVARIA_2026 = {
    (1, 1): "New Year's Day",
    (1, 6): "Epiphany",
    (4, 3): "Good Friday",
    (4, 6): "Easter Monday",
    (5, 1): "Labor Day",
    (5, 14): "Ascension Day",
    (5, 25): "Pentecost Monday",
    (6, 4): "Corpus Christi",
    (8, 15): "Assumption Day",
    (10, 3): "German Unity Day",
    (11, 1): "All Saints' Day",
    (12, 25): "Christmas Day",
    (12, 26): "Second Day of Christmas",
}


def run(command, argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        command(argv)
    return out.getvalue()


def test_lmu_2026_days_off():
    events = LmuSource().year_events(2026)
    expected = {datetime.date(2026, m, d): name for (m, d), name in BAVARIA_2026.items()}
    expected[datetime.date(2026, 12, 24)] = "Christmas Eve (TV-L)"
    expected[datetime.date(2026, 12, 31)] = "New Year's Eve (TV-L)"
    assert events == expected


def test_events_are_limited_to_the_range():
    events = LmuSource().events(datetime.date(2026, 12, 20), datetime.date(2027, 1, 10))
    assert sorted(events) == [
        datetime.date(2026, 12, 24),
        datetime.date(2026, 12, 25),
        datetime.date(2026, 12, 26),
        datetime.date(2026, 12, 31),
        datetime.date(2027, 1, 1),
        datetime.date(2027, 1, 6),
    ]


def test_gcal_lmu_month():
    out = run(gcal_lmu, ["6", "2026", "--color", "never", "--no-next-month"])
    assert out.splitlines()[1] == " Mon  Tue  Wed  Thu  Fri  Sat  Sun"
    assert "    4: Corpus Christi" in out


def test_gcal_sources_option_defaults_to_lmu():
    assert run(gcal, ["6", "2026", "--color", "never"]) == run(gcal_lmu, ["6", "2026", "--color", "never"])


def test_gcal_all_defaults_to_gcal_lmu_all():
    argv = ["2026", "--color", "never"]
    assert run(gcal_all, argv) == run(gcal_lmu_all, argv)


def test_gcal_all_sources():
    argv = ["2026", "--color", "never", "--footnotes"]
    assert run(gcal_all, [*argv, "--sources", "lmu,iran"]) == run(gcal_lmu_iran_all, argv)
    iran = run(gcal_all, [*argv, "--sources", "iran"])
    assert "Norooz" in iran and "German Unity Day" not in iran
