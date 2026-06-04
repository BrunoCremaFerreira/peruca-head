"""Unit tests for PiperSpeaker with a fake PiperVoice injected.

No model is loaded and `piper` is never imported: a warm voice is injected,
mirroring how the composition root injects a once-loaded voice. The test pins
the translation of Piper's AudioChunk stream into a domain AudioBuffer.
"""

from dataclasses import dataclass

import pytest

from domain.models.audio_buffer import AudioBuffer
from infra.tts.piper_speaker import PiperSpeaker


@dataclass
class _FakeChunk:
    """Mimics piper's AudioChunk (only the attributes the adapter reads)."""

    audio_int16_bytes: bytes
    sample_rate: int = 22050
    sample_channels: int = 1
    sample_width: int = 2


class _FakeVoice:
    """Mimics piper.PiperVoice: records the synthesized text, yields chunks."""

    def __init__(self, chunks):
        self._chunks = chunks
        self.synthesized: list[str] = []

    def synthesize(self, text, syn_config=None):
        self.synthesized.append(text)
        return iter(self._chunks)


def test_joins_chunks_into_an_audio_buffer_with_chunk_metadata():
    voice = _FakeVoice(
        [_FakeChunk(b"\x01\x00"), _FakeChunk(b"\x02\x00"), _FakeChunk(b"\x03\x00")]
    )
    speaker = PiperSpeaker(model_path="ignored.onnx", voice=voice)

    buffer = speaker.synthesize("olá")

    assert isinstance(buffer, AudioBuffer)
    assert buffer.pcm == b"\x01\x00\x02\x00\x03\x00"
    assert buffer.sample_rate == 22050
    assert buffer.channels == 1
    assert buffer.sample_width == 2
    assert voice.synthesized == ["olá"]


def test_reads_metadata_from_the_actual_chunk_not_a_hardcoded_rate():
    voice = _FakeVoice([_FakeChunk(b"\x01\x00", sample_rate=16000)])
    speaker = PiperSpeaker(model_path="ignored.onnx", voice=voice)

    buffer = speaker.synthesize("oi")

    assert buffer.sample_rate == 16000


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_blank_text_returns_empty_buffer_without_calling_piper(blank):
    voice = _FakeVoice([_FakeChunk(b"\x01\x00")])
    speaker = PiperSpeaker(model_path="ignored.onnx", voice=voice)

    buffer = speaker.synthesize(blank)

    assert buffer.is_empty()
    assert voice.synthesized == []
