import pathlib
import re
import subprocess
import sys

import pytest

GOLDEN_DIR = pathlib.Path(__file__).parent / "golden"


def run_command(name, args):
    code = f"import sys; from jalali_calendar_cli.commands import {name}; {name}(sys.argv[1:])"
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.mark.parametrize("year", ["1402", "1405"])
def test_jcal_all_matches_perl_baseline(year):
    #: captured from the old `perl jcal_all.pl YEAR --color never`
    expected = (GOLDEN_DIR / f"jcal_all_{year}.txt").read_text()
    assert run_command("jcal_all", [year, "--color", "never"]) == expected


def test_jcal_all_colored_rows_are_aligned():
    out = run_command("jcal_all", ["1405", "--color", "always", "--true-color"])
    widths = {len(re.sub(r"\x1b\[[0-9;]*m", "", line)) for line in out.splitlines() if line.strip()}
    assert len(widths) == 1
