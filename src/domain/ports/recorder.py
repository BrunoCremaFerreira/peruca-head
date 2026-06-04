"""Recorder port: captures speech audio from the microphone.

Records until the speaker stops talking (VAD-driven) and returns the captured
audio as a domain :class:`AudioBuffer`. The capture device and the VAD are hidden
behind this contract; an empty buffer means no speech was detected.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.audio_buffer import AudioBuffer


class Recorder(ABC):
    """Captures a single utterance from the input device."""

    @abstractmethod
    def record_until_silence(self) -> AudioBuffer:
        """Record until sustained silence and return the captured audio.

        Returns an empty :class:`AudioBuffer` when no speech was detected.
        """
        raise NotImplementedError
