"""In-memory fake of the Player port.

Records the buffers it was asked to play (and whether empty ones were skipped),
so use cases can be tested without a real speaker.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.audio_buffer import AudioBuffer
from domain.ports.player import Player


@dataclass
class FakePlayer(Player):
    """A Player that just records what it played."""

    played: list[AudioBuffer] = field(default_factory=list)

    def play(self, buffer: AudioBuffer) -> None:
        self.played.append(buffer)
