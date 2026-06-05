"""Start-cue tone factory: builds a short "you can speak" beep as an AudioBuffer.

This is the only place that synthesizes the cue (DSP lives in infra, never in the
domain). It returns a domain :class:`AudioBuffer` (int16 PCM), so the application
just plays a ready value object via the existing ``Player`` and never touches
numpy. A short fade in/out removes the click at the tone's edges.
"""

from __future__ import annotations

import numpy as np

from domain.models.audio_buffer import AudioBuffer

_INT16_FULL_SCALE = 32767.0


def build_start_cue(
    *,
    sample_rate: int = 16000,
    freq_hz: float = 880.0,
    duration_ms: int = 150,
    fade_ms: int = 10,
    amplitude: float = 0.3,
) -> AudioBuffer:
    """Generate a sine cue tone.

    ``amplitude`` is a fraction of full scale (headroom against saturation);
    ``fade_ms`` is the linear fade applied to each edge.
    """
    frame_count = round(sample_rate * duration_ms / 1000)
    t = np.arange(frame_count, dtype=np.float64) / sample_rate
    wave = np.sin(2.0 * np.pi * freq_hz * t)

    fade_len = min(round(sample_rate * fade_ms / 1000), frame_count // 2)
    if fade_len > 0:
        ramp = np.linspace(0.0, 1.0, fade_len, endpoint=False)
        wave[:fade_len] *= ramp
        wave[-fade_len:] *= ramp[::-1]

    samples = (wave * amplitude * _INT16_FULL_SCALE).astype(np.int16)
    return AudioBuffer(
        pcm=samples.tobytes(),
        sample_rate=sample_rate,
        channels=1,
        sample_width=2,
    )
