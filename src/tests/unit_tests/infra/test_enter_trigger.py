"""Unit tests for EnterTrigger (push-to-talk via stdin)."""

import pytest

from infra.trigger.enter_trigger import EnterTrigger


def test_blocks_on_input_then_returns():
    prompts: list = []
    trigger = EnterTrigger(
        input_fn=lambda prompt="": prompts.append(prompt) or "", prompt="fala> "
    )

    assert trigger.wait_for_trigger() is None
    assert prompts == ["fala> "]


def test_eof_propagates_so_main_can_stop_the_loop():
    def _eof(prompt=""):
        raise EOFError

    trigger = EnterTrigger(input_fn=_eof)

    with pytest.raises(EOFError):
        trigger.wait_for_trigger()
