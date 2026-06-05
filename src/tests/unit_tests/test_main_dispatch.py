"""Unit tests for CLI mode selection (peruca-head <command>)."""

from main import select_mode


def test_no_argument_defaults_to_run():
    # The product is the voice head; bare `peruca-head` runs the loop.
    assert select_mode([]) == "run"


def test_explicit_known_commands():
    assert select_mode(["run"]) == "run"
    assert select_mode(["loop"]) == "loop"
    assert select_mode(["listen"]) == "listen"
    assert select_mode(["chat"]) == "chat"


def test_unknown_command_falls_back_to_run():
    assert select_mode(["nonsense"]) == "run"
