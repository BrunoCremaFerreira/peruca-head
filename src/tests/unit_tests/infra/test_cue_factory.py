"""Unit tests for the start-cue tone factory (pure DSP, infra).

Generates a short sine "you can speak" tone as a domain AudioBuffer. No hardware
is touched; the tone is verified numerically.
"""

import numpy as np

from domain.models.audio_buffer import AudioBuffer
from infra.audio.cue_factory import build_start_cue


def test_returns_16k_mono_int16_audio_buffer():
    cue = build_start_cue()
    assert isinstance(cue, AudioBuffer)
    assert cue.sample_rate == 16000
    assert cue.channels == 1
    assert cue.sample_width == 2


def test_duration_maps_to_frame_count():
    cue = build_start_cue(sample_rate=16000, duration_ms=150)
    assert cue.frame_count == 2400  # 16000 * 0.150


def test_is_an_audible_tone_not_silence():
    samples = np.frombuffer(build_start_cue().pcm, dtype=np.int16)
    assert np.abs(samples).max() > 1000


def test_amplitude_respects_headroom():
    cue = build_start_cue(amplitude=0.3)
    samples = np.frombuffer(cue.pcm, dtype=np.int16)
    # Peak stays under 0.3 of int16 full scale (no saturation).
    assert np.abs(samples).max() <= int(0.3 * 32768) + 1


def test_fades_in_and_out_to_avoid_clicks():
    samples = np.frombuffer(build_start_cue().pcm, dtype=np.int16).astype(np.int64)
    peak = np.abs(samples).max()
    # Edges are quiet (faded) relative to the body of the tone.
    assert abs(samples[0]) < peak // 4
    assert abs(samples[-1]) < peak // 4
