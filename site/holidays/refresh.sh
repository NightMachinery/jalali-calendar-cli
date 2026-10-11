#!/bin/sh
# Regenerates the static holiday page in this directory from the package checkout two
# levels up: index.html, theme.css and app.js, all gitignored since they are built from
# what is committed here (the code, holidays.json, and poetry.lock's holidays version).
#
# Rerunning on the same inputs rewrites nothing. Offline, it falls back to uv's cache;
# if that fails too, it exits non-zero and leaves the previous page in place.
set -eu
cd "$(dirname "$0")"
root=$(cd ../.. && pwd)

if ! command -v uv >/dev/null 2>&1; then
    echo "refresh.sh: uv not found; leaving the page as it is" >&2
    exit 1
fi

run() {
    uv run --quiet "$@" --no-project --with-editable "$root" jcal-html --out .
}

run || run --offline
