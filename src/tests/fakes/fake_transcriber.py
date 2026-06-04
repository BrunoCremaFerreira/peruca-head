"""In-memory fake of the Transcriber port.

Returns a canned Transcript and records the buffers it received, so use cases can
run without Whisper. An empty buffer yields an empty transcript.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.audio_buffer import AudioBuffer
from domain.models.transcript import Transcript
from domain.ports.transcriber import Transcriber


@dataclass
class FakeTranscriber(Transcriber):
    """A scriptable Transcriber."""

    text: str = "bom dia"
    received: list[AudioBuffer] = field(default_factory=list)

    def transcribe(self, audio: AudioBuffer) -> Transcript:
        self.received.append(audio)
        if audio.is_empty():
            return Transcript(text="")
        return Transcript(text=self.text)
