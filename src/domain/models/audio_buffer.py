"""AudioBuffer: an immutable carrier of PCM audio (no DSP in the domain).

It holds raw little-endian PCM bytes exactly as a TTS engine produces them, plus
the metadata a player needs to interpret them (sample rate, channel count,
bytes-per-sample). It deliberately depends on nothing external — not numpy, not
any audio library — so conversion to arrays happens at the infra edge.

Only int16 (``sample_width == 2``) is supported for now; that is what Piper
emits. An empty buffer (``pcm == b""``) is a valid "nothing to play" sentinel.
"""

from __future__ import annotations

from dataclasses import dataclass

_SUPPORTED_SAMPLE_WIDTH = 2  # int16


@dataclass(frozen=True)
class AudioBuffer:
    """Immutable PCM audio plus the metadata needed to play it back."""

    pcm: bytes
    sample_rate: int
    channels: int
    sample_width: int

    def __post_init__(self) -> None:
        if self.channels < 1:
            raise ValueError("channels must be >= 1")
        if self.sample_width != _SUPPORTED_SAMPLE_WIDTH:
            raise ValueError("only int16 audio (sample_width == 2) is supported")
        if self.pcm:
            if self.sample_rate <= 0:
                raise ValueError("sample_rate must be > 0 for non-empty audio")
            frame_size = self.channels * self.sample_width
            if len(self.pcm) % frame_size != 0:
                raise ValueError("pcm length is not aligned to the frame size")

    @classmethod
    def empty(cls) -> "AudioBuffer":
        """A canonical empty buffer: nothing to play."""
        return cls(pcm=b"", sample_rate=0, channels=1, sample_width=_SUPPORTED_SAMPLE_WIDTH)

    def is_empty(self) -> bool:
        """True when there are no samples to play."""
        return len(self.pcm) == 0

    @property
    def frame_count(self) -> int:
        """Number of audio frames (samples per channel)."""
        return len(self.pcm) // (self.channels * self.sample_width)
