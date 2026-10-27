import pathlib
import subprocess
import sys

import pytest

GOLDEN_DIR = pathlib.Path(__file__).parent / "golden"

#: The plain golden files and the `_fri` colored ones were captured from `jcal` before the
#: renderer refactor, when Friday was the only weekend day. The colored ones without
#: `_fri` show the Thursday + Friday weekend.
#: None of these months contain "today", so the output is date-independent.
#: They pin one month at a time, so they all run with `--no-next-month`.
SINGLE_MONTH_CASES = {
    "jcal_7_1402.txt": ["7", "1402", "--color", "never"],
    "jcal_12_1402.txt": ["12", "1402", "--color", "never"],
    "jcal_1_1405.txt": ["1", "1405", "--color", "never"],
    "jcal_12_1405.txt": ["12", "1405", "--color", "never"],
    "jcal_1_1405_compact.txt": [
        "1",
        "1405",
        "--color",
        "never",
        "--no-footnotes",
        "--indentation",
        "4",
        "--line-prefix",
        "",
    ],
    "jcal_7_1402_ansi.txt": ["7", "1402", "--color", "always", "--no-true-color"],
    "jcal_7_1402_ansi_fri.txt": [
        "7",
        "1402",
        "--color",
        "always",
        "--no-true-color",
        "--iran-weekend",
        "fri",
    ],
    "jcal_7_1402_truecolor_dark_fri.txt": [
        "7",
        "1402",
        "--color",
        "always",
        "--true-color",
        "--color-preset",
        "dark",
        "--iran-weekend",
        "fri",
    ],
    "jcal_7_1402_truecolor_dark.txt": [
        "7",
        "1402",
        "--color",
        "always",
        "--true-color",
        "--color-preset",
        "dark",
    ],
}

CASES = {name: [*args, "--no-next-month"] for name, args in SINGLE_MONTH_CASES.items()}
#: Captured after the next month became the default: Esfand 1402 and Farvardin 1403.
CASES["jcal_12_1402_next.txt"] = ["12", "1402", "--color", "never"]


def run_module(module, args):
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.mark.parametrize("golden_name", sorted(CASES))
def test_jcal_matches_golden(golden_name):
    expected = (GOLDEN_DIR / golden_name).read_text()
    actual = run_module("jalali_calendar_cli.jalali_calendar", CASES[golden_name])
    assert actual == expected
