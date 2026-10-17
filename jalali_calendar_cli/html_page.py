##
#: `jcal-html`: a static, self-contained page with every view pre-rendered for a window of
#: years. The page's script only switches views, highlights today and remembers settings;
#: what is a holiday for whom is decided here, by the same model the terminal uses.
##
import argparse
import datetime
import hashlib
import json
import pathlib
import re
from html import escape
from typing import List, Optional

from .calendars import GREGORIAN, JALALI
from .model import build_month
from .render_html import month_html

WEB_DIR = pathlib.Path(__file__).parent / "web"
WEEKDAY_ABBRS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
#: Copied as they are. The PNGs are renders of icon.svg and icon-maskable.svg; see
#: docs/calendars.org for how to redo them.
ICON_FILES = ["icon.svg", "icon-192.png", "icon-512.png", "icon-maskable-512.png", "apple-touch-icon.png"]
#: The shipped icon sets: the files in web/ that each set writes under the names above.
#: "jalali" is the same sheet on a green tile with its weekend column in red, so that two
#: installed calendars can be told apart on a home screen.
ICON_SETS = {
    "calendar": {name: name for name in ICON_FILES},
    "jalali": {
        "icon.svg": "icon-jalali.svg",
        "icon-192.png": "icon-jalali-192.png",
        "icon-512.png": "icon-jalali-512.png",
        "icon-maskable-512.png": "icon-jalali-maskable-512.png",
        "apple-touch-icon.png": "apple-touch-icon-jalali.png",
    },
}
#: the light theme's --bg in theme.css; app.js keeps the browser's bar in step with the theme
THEME_COLOR = "#fbfaf7"

#: (id, button label, grid calendar, primary source name, secondary source name)
VIEWS = [
    ("lmu", "LMU", GREGORIAN, "lmu", None),
    ("lmu-iran", "LMU + Iran", GREGORIAN, "lmu", "iran"),
    ("iran", "Iran", JALALI, "iran", None),
    ("iran-lmu", "Iran + LMU", JALALI, "iran", "lmu"),
]

#: What --config may set, a JSON object in which every key is optional. The defaults are
#: the page as it was before the option existed. `views` lists which views the page has,
#: the first being the one it opens on; a page with one view has no row of view buttons.
DEFAULTS = {
    "views": [view[0] for view in VIEWS],
    #: names the page's localStorage keys and its service worker's cache, so pages on one
    #: origin keep apart; a config that sets it also gives the manifest this `id`
    "app_id": "cal",
    "icon": "calendar",
    "name": "Calendar",
    "short_name": "Calendar",
    "description": "LMU days off and Iranian holidays, alone or overlaid on one grid.",
}
APP_ID = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
#: Keys that a program building the page for a site may add to the same object (the
#: html-reports tool does); they are not the page's business, so they are ignored.
HOST_KEYS = {"device", "path", "origin"}


def load_config(path: Optional[str]) -> dict:
    """--config, checked, over the defaults. An unknown key is an error rather than
    ignored: a misspelt `views` would otherwise build every view, and every source."""
    raw = {}
    if path:
        try:
            raw = json.loads(pathlib.Path(path).read_text())
        except (OSError, ValueError) as exc:
            raise SystemExit(f"jcal-html: --config {path}: {exc}")
    if not isinstance(raw, dict):
        raise SystemExit("jcal-html: --config must hold a JSON object")
    unknown = sorted(set(raw) - set(DEFAULTS) - HOST_KEYS)
    if unknown:
        raise SystemExit(f"jcal-html: unknown config key(s): {', '.join(unknown)}")
    config = dict(DEFAULTS)
    config.update({key: value for key, value in raw.items() if key in DEFAULTS})
    names = [view[0] for view in VIEWS]
    views = config["views"]
    if not isinstance(views, list) or not views or len(set(views)) != len(views) or not set(views) <= set(names):
        raise SystemExit(f"jcal-html: views must list distinct names from {', '.join(names)}")
    for key in ("name", "short_name", "description"):
        if not isinstance(config[key], str) or not config[key].strip():
            raise SystemExit(f"jcal-html: {key} must be a non-empty string")
    if config["icon"] not in ICON_SETS:
        raise SystemExit(f"jcal-html: icon must be one of {', '.join(ICON_SETS)}")
    if not isinstance(config["app_id"], str) or not APP_ID.match(config["app_id"]):
        raise SystemExit("jcal-html: app_id must be lowercase letters, digits and dashes")
    #: only when asked for: an installed app is known by its manifest id, and giving the
    #: default page one now would make existing installs a different app
    config["manifest_id"] = config["app_id"] if "app_id" in raw else None
    return config


def chosen_views(config: dict) -> list:
    by_id = {view[0]: view for view in VIEWS}
    return [by_id[view_id] for view_id in config["views"]]


def needed_sources(config: dict) -> list:
    """The holiday sources the chosen views read, so no other is loaded at all."""
    names = []
    for _, _, _, primary, secondary in chosen_views(config):
        for name in (primary, secondary):
            if name and name not in names:
                names.append(name)
    return names


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


def web_manifest(config: dict) -> str:
    #: relative URLs: the page is served under a subpath, and from any --out directory
    manifest = {
        **({"id": config["manifest_id"]} if config.get("manifest_id") else {}),
        "name": config["name"],
        "short_name": config["short_name"],
        "description": config["description"],
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": THEME_COLOR,
        "theme_color": THEME_COLOR,
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return json.dumps(manifest, indent=2) + "\n"


def build_page(sources: dict, first_year: int, last_year: int, config: Optional[dict] = None) -> dict:
    """Returns {file name: content} for the page: text as str, the icons as bytes.
    `sources` needs only the ones the configured views read (needed_sources)."""
    config = config or DEFAULTS
    css = (WEB_DIR / "theme.css").read_text()
    js = (WEB_DIR / "app.js").read_text()

    views = chosen_views(config)
    buttons: List[str] = []
    legends: List[str] = []
    months: List[str] = []
    for view_id, label, calendar, primary_name, secondary_name in views:
        primary = sources[primary_name]
        secondary = sources[secondary_name] if secondary_name else None
        buttons.append(f'<button type="button" data-set-view="{view_id}">{escape(label)}</button>')
        legends.append(legend_html(view_id, primary, secondary))
        for year in year_range(calendar, first_year, last_year):
            for month in range(1, 13):
                model = build_month(calendar, primary, secondary, year, month)
                months.append(month_html(model, view_id, calendar))
    #: one view needs no buttons to choose it
    nav = (
        f'<nav class="views" aria-label="Holiday sets">{"".join(buttons)}</nav>\n'
        if len(views) > 1
        else ""
    )

    index = f"""<!doctype html>
<html lang="en" data-theme="light" data-app="{config["app_id"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(config["name"])}</title>
<link rel="manifest" href="manifest.webmanifest" crossorigin="use-credentials">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="theme-color" content="{THEME_COLOR}">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{escape(config["short_name"])}">
<link rel="stylesheet" href="theme.css?v={short_hash(css)}">
<script>try{{var t=localStorage.getItem("{config["app_id"]}-theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
<header>
{nav}<div class="controls">
<button type="button" id="prev" aria-label="Previous">&#8249;</button>
<button type="button" id="today">Today</button>
<button type="button" id="next" aria-label="Next">&#8250;</button>
<span class="spacer"></span>
<span class="modes"><button type="button" data-set-mode="month">Month</button><button type="button" data-set-mode="year">Year</button></span>
<button type="button" id="theme" aria-label="Switch light and dark theme">&#9680;</button>
<button type="button" id="key-toggle" aria-label="Color key and settings" aria-controls="key" aria-expanded="false">&#9881;&#xFE0E;</button>
</div>
</header>
<!-- not in the sticky header: on a phone it would cover half the screen; collapsed by default -->
<div class="key" id="key" hidden>
{"".join(legends)}
<div class="options">
<label class="option"><input type="checkbox" id="show-notes"> Holiday list</label>
<label class="option" data-mode="month"><input type="checkbox" id="show-next-month"> Next month</label>
<label class="option" data-mode="year"><input type="checkbox" id="show-next-row"> Next year's start</label>
</div>
</div>
<main id="months" class="month">
{chr(10).join(months)}
</main>
<noscript><p>This page needs JavaScript to choose which month to show.</p></noscript>
<script src="app.js?v={short_hash(js)}"></script>
</body>
</html>
"""
    files = {
        "index.html": index,
        "theme.css": css,
        "app.js": js,
        "manifest.webmanifest": web_manifest(config),
        "sw.js": (WEB_DIR / "sw.js").read_text().replace("__APP__", config["app_id"]),
    }
    files.update({name: (WEB_DIR / src).read_bytes() for name, src in ICON_SETS[config["icon"]].items()})
    return files


def write_if_changed(path: pathlib.Path, content) -> bool:
    data = content.encode() if isinstance(content, str) else content
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def main(argv: Optional[list] = None) -> None:
    from .cli import add_source_args, make_source

    this_year = datetime.date.today().year
    parser = argparse.ArgumentParser(
        prog="jcal-html",
        description="Write a static HTML page with the Gregorian and Jalali calendars and their holidays.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="directory to write the page to: index.html, app.js, theme.css, the web app manifest, icons and sw.js",
    )
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
    parser.add_argument(
        "--config",
        help="JSON file of page settings: views, name, short_name, description (see docs/calendars.org)",
    )
    add_source_args(parser)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    sources = {name: make_source(name, args) for name in needed_sources(config)}
    files = build_page(sources, args.from_year, args.to_year, config)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        changed = write_if_changed(out / name, content)
        print(f"{'wrote' if changed else 'unchanged'}: {out / name}")


if __name__ == "__main__":
    main()
