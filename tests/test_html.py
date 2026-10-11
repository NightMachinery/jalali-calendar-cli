import hashlib
import json
import pathlib
import re
from html import unescape

from jalali_calendar_cli.calendars import GREGORIAN
from jalali_calendar_cli.html_page import build_page, main
from jalali_calendar_cli.model import build_month
from jalali_calendar_cli.render_html import month_html
from jalali_calendar_cli.sources.iran import IranSource
from jalali_calendar_cli.sources.lmu import LmuSource


def cell_tags(html):
    """{day: the attributes of its <td>}"""
    return {int(day): attrs for attrs, day in re.findall(r"<td([^>]*)><span>(\d+)</span></td>", html)}


def test_month_cells_carry_roles():
    model = build_month(GREGORIAN, LmuSource(), IranSource(), 2026, 6)
    html = month_html(model, "lmu-iran", GREGORIAN)
    assert 'data-start="2026-06-01" data-end="2026-06-30"' in html
    cells = cell_tags(html)
    #: Jun 4 and 5 are a Thursday and a Friday: in the Iranian weekend columns
    assert cells[4].startswith(' class="ph sh sw both" data-tip=')
    assert cells[5].startswith(' class="sh sw" data-tip=')
    assert cells[11] == ' class="sw"'
    assert cells[24].startswith(' class="sh" data-tip=')
    assert cells[6] == ' class="pw"'
    assert '<span class="native">14 Khordad</span>' in html


def test_tooltips_carry_holidays_and_the_other_calendar():
    model = build_month(GREGORIAN, LmuSource(), IranSource(), 2026, 6)
    html = month_html(model, "lmu-iran", GREGORIAN)
    tip = json.loads(unescape(re.search(r'<td class="ph sh sw both" data-tip="([^"]*)"', html).group(1)))
    assert tip["b"] == 1
    assert ["LMU", "Corpus Christi", 0] in tip["h"]
    assert any(tag == "IR" and secondary == 1 for tag, _, secondary in tip["h"])
    #: June 2026 starts on 11 Khordad 1405, and 1 Tir is June 22
    other = json.loads(unescape(re.search(r'data-other="([^"]*)"', html).group(1)))
    assert other == [[1, 11, "Khordad", 1405], [22, 1, "Tir", 1405]]
    assert 'data-label="June 2026"' in html


def test_jalali_grid_tooltips_carry_gregorian_dates():
    from jalali_calendar_cli.calendars import JALALI

    model = build_month(JALALI, IranSource(), LmuSource(), 1405, 10)
    html = month_html(model, "iran-lmu", JALALI)
    other = json.loads(unescape(re.search(r'data-other="([^"]*)"', html).group(1)))
    #: 1 Dey 1405 is Dec 22, 2026; Jan 1, 2027 is 11 Dey
    assert other == [[1, 22, "December", 2026], [11, 1, "January", 2027]]


def test_every_week_row_has_seven_cells():
    model = build_month(GREGORIAN, LmuSource(), None, 2026, 3)
    html = month_html(model, "lmu", GREGORIAN)
    rows = re.findall(r"<tr>(.*?)</tr>", html.split("<tbody>")[1])
    assert rows and all(row.count("<td") == 7 for row in rows)


def test_page_has_all_views_and_years():
    files = build_page({"lmu": LmuSource(), "iran": IranSource()}, 2026, 2026)
    index = files["index.html"]
    for view in ("lmu", "lmu-iran", "iran", "iran-lmu"):
        assert f'data-set-view="{view}"' in index
        assert f'class="legend" data-view="{view}"' in index
    #: 12 Gregorian months per Gregorian view, and the Jalali years 1404 and 1405 per Jalali view
    assert index.count('data-view="lmu" data-year="2026"') == 12
    assert index.count('data-view="iran" data-year="1404"') == 12
    assert index.count('data-view="iran" data-year="1405"') == 12


def tree_hash(directory: pathlib.Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.iterdir()):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_generation_is_idempotent(tmp_path, capsys):
    argv = ["--out", str(tmp_path), "--from-year", "2026", "--to-year", "2027"]
    main(argv)
    first = tree_hash(tmp_path)
    capsys.readouterr()
    main(argv)
    assert tree_hash(tmp_path) == first
    assert capsys.readouterr().out.count("unchanged:") == 3


def test_holiday_lists_have_a_switch():
    files = build_page({"lmu": LmuSource(), "iran": IranSource()}, 2026, 2026)
    assert 'id="show-notes"' in files["index.html"]
    assert 'id="show-next-month"' in files["index.html"]
    assert 'id="show-next-row"' in files["index.html"]
    assert "main.hide-notes .notes" in files["theme.css"]
    #: the holiday lists start hidden, the next month and row shown
    assert 'option("show-notes", "cal-notes", false' in files["app.js"]
    assert 'option("show-next-month", "cal-next-month", true' in files["app.js"]
    assert 'option("show-next-row", "cal-next-row", true' in files["app.js"]
