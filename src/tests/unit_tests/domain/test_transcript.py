"""Unit tests for the Transcript value object (mirrors Reply)."""

import pytest

from domain.models.transcript import Transcript


def test_exposes_its_text():
    assert Transcript(text="bom dia").text == "bom dia"


def test_is_immutable():
    transcript = Transcript(text="bom dia")
    with pytest.raises(Exception):
        transcript.text = "outro"  # type: ignore[misc]


def test_equality_is_by_value():
    assert Transcript(text="oi") == Transcript(text="oi")
    assert Transcript(text="oi") != Transcript(text="tchau")


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_is_empty_true_for_blank_text(text):
    assert Transcript(text=text).is_empty() is True


def test_is_empty_false_for_real_text():
    assert Transcript(text="oi").is_empty() is False
