"""VoiceLoop: the push-to-talk state machine that repeats a voice turn.

Pure orchestration — no I/O, no device or model access. It owns the IDLE state
and the loop; the turn owns LISTENING/THINKING/SPEAKING. Triggering and the
continue/stop decision are injected callables (a ``Trigger`` port arrives only in
Phase 5):

- ``wait_for_trigger`` blocks until the user pushes to talk (Enter); its return
  value is ignored.
- ``should_continue`` decides whether to keep looping (so it is testable and so
  ``main`` can stop the loop).
- ``on_state`` receives IDLE transitions for console/LED feedback.

The anti-echo property (the next turn's capture only starts after the previous
playback finished) is structural: the loop is sequential and single-threaded and
``Player.play`` is blocking, so there is no flag to manage here. Every turn ends
back at IDLE because the turn never propagates a brain error.
"""

from __future__ import annotations

from typing import Callable, Optional

from domain.models.voice_state import VoiceState


class VoiceLoop:
    """Repeats a voice turn, one per push-to-talk trigger."""

    def __init__(
        self,
        turn,
        *,
        wait_for_trigger: Callable[[], object],
        should_continue: Callable[[], bool],
        on_state: Optional[Callable[[VoiceState], None]] = None,
    ) -> None:
        self._turn = turn
        self._wait_for_trigger = wait_for_trigger
        self._should_continue = should_continue
        self._on_state = on_state or (lambda state: None)

    def run(self) -> None:
        while self._should_continue():
            self._on_state(VoiceState.IDLE)
            self._wait_for_trigger()
            self._turn.run()
        self._on_state(VoiceState.IDLE)  # always come to rest at IDLE
