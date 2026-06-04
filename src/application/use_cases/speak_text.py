"""SpeakTextUseCase: synthesize text and play it.

The Phase 1 vertical slice for voice output: ``text -> Speaker -> Player``.
It depends only on the :class:`Speaker` and :class:`Player` ports, so neither
Piper nor sounddevice is visible here. Empty text/audio falls through harmlessly
(the speaker yields an empty buffer, the player skips it).
"""

from __future__ import annotations

from domain.ports.player import Player
from domain.ports.speaker import Speaker


class SpeakTextUseCase:
    """Renders text to speech and plays it on the output device."""

    def __init__(self, speaker: Speaker, player: Player) -> None:
        self._speaker = speaker
        self._player = player

    def run(self, text: str) -> None:
        buffer = self._speaker.synthesize(text)
        if buffer.is_empty():
            return
        self._player.play(buffer)
