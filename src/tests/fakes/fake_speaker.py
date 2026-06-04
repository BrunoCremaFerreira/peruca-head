"""In-memory fake of the Speaker port.

Returns a canned AudioBuffer and records the texts it was asked to synthesize,
so use cases can be exercised without Piper or any model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.audio_buffer import AudioBuffer
from domain.ports.speaker import Speaker

_CANNED = AudioBuffer(pcm=b"\x01\x00\x02\x00", sample_rate=22050, channels=1, sample_width=2)


@dataclass
class FakeSpeaker(Speaker):
    """A scriptable Speaker. Empty/blank text yields an empty buffer."""

    buffer: AudioBuffer = _CANNED
    texts: list[str] = field(default_factory=list)

    def synthesize(self, text: str) -> AudioBuffer:
        self.texts.append(text)
        if text.strip() == "":
            return AudioBuffer.empty()
        return self.buffer
