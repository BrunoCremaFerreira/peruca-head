"""Speaker port: turns text into speech audio.

Speaks only in domain types (``str`` in, :class:`AudioBuffer` out). The
synthesis engine (Piper, or any other) is hidden behind this contract.

The single-:class:`AudioBuffer` return intentionally keeps Phase 1 batch-only;
streaming (``Iterable[AudioBuffer]``) is deferred until replies get long enough
that time-to-first-audio matters (Phase 3+).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.audio_buffer import AudioBuffer


class Speaker(ABC):
    """Synthesizes speech audio from text."""

    @abstractmethod
    def synthesize(self, text: str) -> AudioBuffer:
        """Render ``text`` to speech. Empty/blank text yields an empty buffer."""
        raise NotImplementedError
