"""Unit tests for the Reply value object."""

import pytest

from domain.models.reply import Reply


def test_reply_exposes_its_text():
    assert Reply(text="olá").text == "olá"


def test_reply_is_immutable():
    reply = Reply(text="olá")
    with pytest.raises(Exception):
        reply.text = "outro"  # type: ignore[misc]


def test_reply_equality_is_by_value():
    assert Reply(text="oi") == Reply(text="oi")
    assert Reply(text="oi") != Reply(text="tchau")


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_is_empty_true_for_blank_text(text):
    assert Reply(text=text).is_empty() is True


def test_is_empty_false_for_real_text():
    assert Reply(text="oi").is_empty() is False
