"""Player port: plays speech audio on an output device.

Separate from :class:`Speaker` and from a future ``Recorder`` so capturing and
playing stay independently mockable. Speaks only in domain types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.audio_buffer import AudioBuffer


class Player(ABC):
    """Plays an :class:`AudioBuffer` on the output device."""

    @abstractmethod
    def play(self, buffer: AudioBuffer) -> None:
        """Play ``buffer``. An empty buffer is a no-op (nothing to play)."""
        raise NotImplementedError
