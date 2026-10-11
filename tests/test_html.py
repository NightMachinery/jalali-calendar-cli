import hashlib
import pathlib
import re

from jalali_calendar_cli.calendars import GREGORIAN
from jalali_calendar_cli.html_page import build_page, main
from jalali_calendar_cli.model import build_month
from jalali_calendar_cli.render_html import month_html
from jalali_calendar_cli.sources.iran import IranSource
from jalali_calendar_cli.sources.lmu import LmuSource


def test_month_cells_carry_roles():
    model = build_month(GREGORIAN, LmuSource(), IranSource(), 2026, 6)
    html = month_html(model, "lmu-iran")
    assert 'data-start="2026-06-01" data-end="2026-06-30"' in html
    assert '<td class="ph sh both">4</td>' in html
    assert '<td class="sh">5</td>' in html
    assert '<td class="sw">11</td>' in html
    assert '<td class="sh">24</td>' in html
    assert '<td class="pw">6</td>' in html
    assert '<span class="native">14 Khordad</span>' in html


def test_every_week_row_has_seven_cells():
    model = build_month(GREGORIAN, LmuSource(), None, 2026, 3)
    html = month_html(model, "lmu")
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
