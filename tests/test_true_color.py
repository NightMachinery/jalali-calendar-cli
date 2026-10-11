import argparse

import pytest

from jalali_calendar_cli.cli import (
    add_display_args,
    display_options_from_args,
    terminal_supports_true_color,
)


@pytest.mark.parametrize(
    "environ, expected",
    [
        ({"COLORTERM": "truecolor"}, True),
        ({"COLORTERM": "24bit"}, True),
        ({"TERM": "xterm-256color", "COLORTERM": ""}, False),
        ({"TERM": "xterm-direct"}, True),
        ({"TERM": "xterm-kitty"}, True),
        ({"TERM": "screen-256color", "TERM_PROGRAM": "iTerm.app"}, True),
        ({"TERM": "xterm-256color", "TERM_PROGRAM": "Apple_Terminal"}, False),
        ({}, False),
    ],
)
def test_detection(environ, expected):
    assert terminal_supports_true_color(environ) is expected


def true_color_for(argv, monkeypatch, colorterm):
    monkeypatch.setenv("COLORTERM", colorterm)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    parser = argparse.ArgumentParser()
    add_display_args(parser)
    return display_options_from_args(parser.parse_args(argv)).true_color


def test_default_follows_the_terminal(monkeypatch):
    assert true_color_for([], monkeypatch, "truecolor") is True
    assert true_color_for([], monkeypatch, "") is False


def test_explicit_flags_win(monkeypatch):
    assert true_color_for(["--no-true-color"], monkeypatch, "truecolor") is False
    assert true_color_for(["--true-color"], monkeypatch, "") is True
