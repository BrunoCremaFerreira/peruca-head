"""VoiceTurnUseCase: one full turn of the voice loop.

Composes the existing use cases (Listen -> TextTurn -> SpeakText) rather than the
raw ports, so their tested empty/error invariants are reused, not duplicated. It
adds only what is genuinely turn-level:

- emit LISTENING/THINKING/SPEAKING state transitions (via an injected callback);
- short-circuit before asking the brain when nothing was heard;
- catch a brain failure, speak a pt-BR error instead, and NOT propagate it;
- per-stage timing (listen / brain / speak), with the brain isolated, via an
  injected clock and callback.

It returns a :class:`TurnOutcome` so the loop and the tests can assert what
happened without inspecting I/O.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from application.use_cases.listen import ListenUseCase
from application.use_cases.speak_text import SpeakTextUseCase
from application.use_cases.text_turn import TextTurnUseCase
from domain.models.audio_buffer import AudioBuffer
from domain.models.turn_outcome import TurnOutcome
from domain.models.voice_state import VoiceState
from domain.ports.brain_client import BrainUnavailableError


class VoiceTurnUseCase:
    """Runs one record -> transcribe -> ask -> speak turn."""

    def __init__(
        self,
        listen: ListenUseCase,
        text_turn: TextTurnUseCase,
        speak: SpeakTextUseCase,
        *,
        error_phrase: str,
        on_state: Optional[Callable[[VoiceState], None]] = None,
        on_timing: Optional[Callable[[str, float], None]] = None,
        clock: Optional[Callable[[], float]] = None,
        start_cue: Optional[AudioBuffer] = None,
        play_cue: Optional[Callable[[AudioBuffer], None]] = None,
    ) -> None:
        self._listen = listen
        self._text_turn = text_turn
        self._speak = speak
        self._error_phrase = error_phrase
        self._on_state = on_state or (lambda state: None)
        self._on_timing = on_timing or (lambda label, seconds: None)
        self._clock = clock or time.perf_counter
        self._start_cue = start_cue
        self._play_cue = play_cue

    def run(self) -> TurnOutcome:
        self._on_state(VoiceState.LISTENING)
        # Signal "you can speak" before capture opens, so the cue can't leak in.
        if self._start_cue is not None and self._play_cue is not None:
            self._play_cue(self._start_cue)
        transcript = self._timed("listen", self._listen.run)
        if transcript.is_empty():
            return TurnOutcome.EMPTY

        self._on_state(VoiceState.THINKING)
        try:
            reply = self._timed("brain", lambda: self._text_turn.run(transcript.text))
        except BrainUnavailableError:
            self._on_state(VoiceState.SPEAKING)
            self._speak.run(self._error_phrase)
            return TurnOutcome.BRAIN_ERROR

        self._on_state(VoiceState.SPEAKING)
        self._timed("speak", lambda: self._speak.run(reply.text))
        return TurnOutcome.SUCCESS

    def _timed(self, label: str, action: Callable[[], object]) -> object:
        start = self._clock()
        try:
            return action()
        finally:
            # Emit even on failure, so a brain timeout's latency is still logged.
            self._on_timing(label, self._clock() - start)
