"""Transcriber port: turns speech audio into text.

Speaks only in domain types (:class:`AudioBuffer` in, :class:`Transcript` out).
The STT engine (Whisper, or any other) is hidden behind this contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.audio_buffer import AudioBuffer
from domain.models.transcript import Transcript


class Transcriber(ABC):
    """Transcribes speech audio into text."""

    @abstractmethod
    def transcribe(self, audio: AudioBuffer) -> Transcript:
        """Recognise the speech in ``audio``. Empty audio yields an empty transcript."""
        raise NotImplementedError
