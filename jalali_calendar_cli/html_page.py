##
#: `jcal-html`: a static, self-contained page with every view pre-rendered for a window of
#: years. The page's script only switches views, highlights today and remembers settings;
#: what is a holiday for whom is decided here, by the same model the terminal uses.
##
import argparse
import datetime
import hashlib
import pathlib
from html import escape
from typing import List, Optional

from .calendars import GREGORIAN, JALALI
from .model import build_month
from .render_html import month_html

WEB_DIR = pathlib.Path(__file__).parent / "web"
WEEKDAY_ABBRS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

#: (id, button label, grid calendar, primary source name, secondary source name)
VIEWS = [
    ("lmu", "LMU", GREGORIAN, "lmu", None),
    ("lmu-iran", "LMU + Iran", GREGORIAN, "lmu", "iran"),
    ("iran", "Iran", JALALI, "iran", None),
    ("iran-lmu", "Iran + LMU", JALALI, "iran", "lmu"),
]


def weekend_text(source) -> str:
    return ", ".join(WEEKDAY_ABBRS[wd] for wd in sorted(source.weekend))


def legend_html(view_id: str, primary, secondary) -> str:
    #: Each swatch is a sample day cell; the same number in all of them, so that it reads
    #: as "a day looks like this" and not as a date.
    def item(classes, text):
        return (
            f'<span class="item"><span class="swatch {classes}" aria-hidden="true">12</span>'
            f"{escape(text)}</span>"
        )

    items = [
        item("ph", f"{primary.label} holiday"),
        item("pw", f"{primary.label} weekend ({weekend_text(primary)})"),
    ]
    if secondary:
        items += [
            item("sh", f"{secondary.label} holiday"),
            item("sw", f"{secondary.label} weekend ({weekend_text(secondary)})"),
            item("ph both", "both free"),
        ]
    return f'<div class="legend" data-view="{view_id}" hidden>{"".join(items)}</div>'


def year_range(calendar, first_gregorian_year: int, last_gregorian_year: int) -> range:
    if calendar is GREGORIAN:
        return range(first_gregorian_year, last_gregorian_year + 1)
    first = calendar.from_gregorian(datetime.date(first_gregorian_year, 1, 1))[0]
    last = calendar.from_gregorian(datetime.date(last_gregorian_year, 12, 31))[0]
    return range(first, last + 1)


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:10]


def build_page(sources: dict, first_year: int, last_year: int) -> dict:
    """Returns {file name: content} for the page."""
    css = (WEB_DIR / "theme.css").read_text()
    js = (WEB_DIR / "app.js").read_text()

    buttons: List[str] = []
    legends: List[str] = []
    months: List[str] = []
    for view_id, label, calendar, primary_name, secondary_name in VIEWS:
        primary = sources[primary_name]
        secondary = sources[secondary_name] if secondary_name else None
        buttons.append(f'<button type="button" data-set-view="{view_id}">{escape(label)}</button>')
        legends.append(legend_html(view_id, primary, secondary))
        for year in year_range(calendar, first_year, last_year):
            for month in range(1, 13):
                model = build_month(calendar, primary, secondary, year, month)
                months.append(month_html(model, view_id))

    index = f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Holidays</title>
<link rel="stylesheet" href="theme.css?v={short_hash(css)}">
<script>try{{var t=localStorage.getItem("cal-theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
<header>
<nav class="views" aria-label="Holiday sets">{"".join(buttons)}</nav>
<div class="controls">
<button type="button" id="prev" aria-label="Previous">&#8249;</button>
<button type="button" id="today">Today</button>
<button type="button" id="next" aria-label="Next">&#8250;</button>
<span class="spacer"></span>
<span class="modes"><button type="button" data-set-mode="month">Month</button><button type="button" data-set-mode="year">Year</button></span>
<button type="button" id="theme" aria-label="Switch light and dark theme">&#9680;</button>
</div>
{"".join(legends)}
</header>
<main id="months" class="month">
{chr(10).join(months)}
</main>
<noscript><p>This page needs JavaScript to choose which month to show.</p></noscript>
<script src="app.js?v={short_hash(js)}"></script>
</body>
</html>
"""
    return {"index.html": index, "theme.css": css, "app.js": js}


def write_if_changed(path: pathlib.Path, content: str) -> bool:
    if path.exists() and path.read_text() == content:
        return False
    path.write_text(content)
    return True


def main(argv: Optional[list] = None) -> None:
    from .cli import add_source_args, make_source

    this_year = datetime.date.today().year
    parser = argparse.ArgumentParser(
        prog="jcal-html",
        description="Write a static HTML page with the Gregorian and Jalali calendars and their holidays.",
    )
    parser.add_argument("--out", required=True, help="directory to write index.html, app.js and theme.css to")
    parser.add_argument(
        "--from-year",
        type=int,
        default=this_year - 1,
        help="first Gregorian year to include (default: last year)",
    )
    parser.add_argument(
        "--to-year",
        type=int,
        default=this_year + 2,
        help="last Gregorian year to include (default: two years from now)",
    )
    add_source_args(parser)
    args = parser.parse_args(argv)

    sources = {name: make_source(name, args) for name in ("lmu", "iran")}
    files = build_page(sources, args.from_year, args.to_year)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        changed = write_if_changed(out / name, content)
        print(f"{'wrote' if changed else 'unchanged'}: {out / name}")


if __name__ == "__main__":
    main()
