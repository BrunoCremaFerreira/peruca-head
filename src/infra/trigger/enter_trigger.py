"""EnterTrigger: push-to-talk — wait for the user to press Enter.

Encapsulates the stdin wait (external I/O) behind the :class:`Trigger` port so
the composition root can choose it symmetrically with the wake-word trigger.
``input_fn`` is injected so the trigger is testable without a terminal; EOFError
propagates so ``main`` can end the loop.
"""

from __future__ import annotations

from typing import Callable

from domain.ports.trigger import Trigger


class EnterTrigger(Trigger):
    """Blocks until the user presses Enter."""

    def __init__(
        self,
        *,
        input_fn: Callable[..., str] = input,
        prompt: str = "press Enter and speak… ",
    ) -> None:
        self._input_fn = input_fn
        self._prompt = prompt

    def wait_for_trigger(self) -> None:
        self._input_fn(self._prompt)
