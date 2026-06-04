"""In-memory fake of the Recorder port.

Returns a canned AudioBuffer (16k mono int16 by default) and counts how many
times it was asked to record, so use cases can run without a microphone or VAD.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.audio_buffer import AudioBuffer
from domain.ports.recorder import Recorder

_CANNED = AudioBuffer(pcm=b"\x01\x00\x02\x00", sample_rate=16000, channels=1, sample_width=2)


@dataclass
class FakeRecorder(Recorder):
    """A Recorder that yields a fixed buffer and counts calls."""

    buffer: AudioBuffer = _CANNED
    calls: int = 0

    def record_until_silence(self) -> AudioBuffer:
        self.calls += 1
        return self.buffer
