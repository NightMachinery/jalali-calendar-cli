#!/bin/sh
# Regenerates the static holiday page in this directory from the package checkout two
# levels up: index.html, theme.css and app.js, all gitignored since they are built from
# what is committed here (the code, holidays.json, and poetry.lock's holidays version).
#
# Rerunning on the same inputs rewrites nothing. Offline, it falls back to uv's cache;
# if that fails too, it exits non-zero and leaves the previous page in place.
#
# A site builder that makes several pages from this one (the html-reports tool does) sets
# HTML_REPORTS_OUT to an absolute directory to write to instead, and HTML_REPORTS_CONFIG
# to a jcal-html --config file. Run by hand, neither is set.
set -eu
cd "$(dirname "$0")"
root=$(cd ../.. && pwd)
out=${HTML_REPORTS_OUT:-.}
config=${HTML_REPORTS_CONFIG:-}

if ! command -v uv >/dev/null 2>&1; then
    echo "refresh.sh: uv not found; leaving the page as it is" >&2
    exit 1
fi

run() {
    if [ -n "$config" ]; then
        uv run --quiet "$@" --no-project --with-editable "$root" jcal-html --out "$out" --config "$config"
    else
        uv run --quiet "$@" --no-project --with-editable "$root" jcal-html --out "$out"
    fi
}

run || run --offline
