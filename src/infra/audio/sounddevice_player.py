"""SoundDevicePlayer: the Player adapter backed by sounddevice (PortAudio).

The only module aware of ``sounddevice``. It views the buffer's raw PCM as an
int16 numpy array and plays it at the buffer's own sample rate, so there is no
resampling on the critical path when Piper and the device agree (both 22050 Hz).

``sounddevice`` is imported lazily because it loads the system PortAudio library
at import time; deferring that import keeps this module importable (and unit
tests runnable, with the backend injected) on machines without PortAudio.
Playback is blocking (``play`` + ``wait``); a callback/barge-in path is deferred
to a later phase.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from domain.models.audio_buffer import AudioBuffer
from domain.ports.player import Player


class SoundDevicePlayer(Player):
    """Plays int16 PCM on the default output device via PortAudio."""

    def __init__(self, *, backend: Optional[Any] = None) -> None:
        """``backend`` injects a sounddevice-like module (used by tests); when
        omitted, the real ``sounddevice`` is imported lazily on first use."""
        self._backend = backend

    def play(self, buffer: AudioBuffer) -> None:
        if buffer.is_empty():
            return

        array = np.frombuffer(buffer.pcm, dtype="int16")
        if buffer.channels > 1:
            array = array.reshape(-1, buffer.channels)

        backend = self._sounddevice()
        backend.play(array, samplerate=buffer.sample_rate)
        backend.wait()

    def _sounddevice(self) -> Any:
        if self._backend is None:
            import sounddevice

            self._backend = sounddevice
        return self._backend
