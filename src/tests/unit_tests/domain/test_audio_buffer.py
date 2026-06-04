"""Unit tests for the AudioBuffer value object.

AudioBuffer is a thin, immutable carrier of PCM audio (no DSP in the domain).
It holds raw little-endian PCM bytes plus the metadata a player needs to
interpret them, and never depends on numpy or any audio library.
"""

import pytest

from domain.models.audio_buffer import AudioBuffer

# 2 frames of mono int16 = 4 bytes.
_TWO_FRAMES = b"\x01\x00\x02\x00"


def test_exposes_pcm_and_metadata():
    buffer = AudioBuffer(pcm=_TWO_FRAMES, sample_rate=22050, channels=1, sample_width=2)
    assert buffer.pcm == _TWO_FRAMES
    assert buffer.sample_rate == 22050
    assert buffer.channels == 1
    assert buffer.sample_width == 2


def test_is_immutable():
    buffer = AudioBuffer(pcm=_TWO_FRAMES, sample_rate=22050, channels=1, sample_width=2)
    with pytest.raises(Exception):
        buffer.sample_rate = 16000  # type: ignore[misc]


def test_equality_is_by_value():
    a = AudioBuffer(pcm=_TWO_FRAMES, sample_rate=22050, channels=1, sample_width=2)
    b = AudioBuffer(pcm=_TWO_FRAMES, sample_rate=22050, channels=1, sample_width=2)
    assert a == b


def test_frame_count_counts_frames():
    buffer = AudioBuffer(pcm=_TWO_FRAMES, sample_rate=22050, channels=1, sample_width=2)
    assert buffer.frame_count == 2


def test_non_empty_buffer_is_not_empty():
    buffer = AudioBuffer(pcm=_TWO_FRAMES, sample_rate=22050, channels=1, sample_width=2)
    assert buffer.is_empty() is False


def test_empty_factory_produces_an_empty_buffer():
    buffer = AudioBuffer.empty()
    assert buffer.is_empty() is True
    assert buffer.pcm == b""
    assert buffer.frame_count == 0


def test_rejects_pcm_not_aligned_to_frame_size():
    # 3 bytes cannot tile mono int16 (2-byte) frames.
    with pytest.raises(ValueError):
        AudioBuffer(pcm=b"\x01\x00\x02", sample_rate=22050, channels=1, sample_width=2)


def test_rejects_non_positive_sample_rate_for_real_audio():
    with pytest.raises(ValueError):
        AudioBuffer(pcm=_TWO_FRAMES, sample_rate=0, channels=1, sample_width=2)


def test_rejects_unsupported_sample_width():
    with pytest.raises(ValueError):
        AudioBuffer(pcm=_TWO_FRAMES, sample_rate=22050, channels=1, sample_width=1)


def test_rejects_zero_channels():
    with pytest.raises(ValueError):
        AudioBuffer(pcm=_TWO_FRAMES, sample_rate=22050, channels=0, sample_width=2)
