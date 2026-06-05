"""SoundDeviceRecorder: the Recorder adapter (sounddevice capture + silero VAD).

The only module aware of ``sounddevice`` (capture) and the VAD. It captures
16 kHz mono int16 frames (so there is no resampling on the path to Whisper),
runs each frame through a voice-activity detector, and records from speech onset
until sustained silence — prepending a short pre-roll so the first syllable is
not clipped.

Both heavy collaborators are injectable and lazily built:
- ``vad``: a ``callable(float32_frame) -> speech_probability``; by default a
  silero-vad model (which pulls in torch) loaded lazily.
- ``frame_source_factory``: a ``callable() -> Iterable[int16 ndarray]`` yielding
  fixed-size frames; by default a sounddevice input stream.

This keeps the module importable and unit-testable with no microphone, torch, or
PortAudio (tests inject scripted frames and a scripted VAD). Silero requires
exactly 512-sample frames at 16 kHz, so the default capture uses that block size.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Iterable, Optional

import numpy as np

import time

from domain.models.audio_buffer import AudioBuffer
from domain.ports.recorder import Recorder

_SILERO_FRAME_SIZE = 512  # silero-vad accepts only 512 samples at 16 kHz
_INT16_FULL_SCALE = 32768.0
# Silence waited before opening the input stream, so the start cue's acoustic
# tail/reverb has died before capture begins (anti-leak). Not configurable.
_PRE_CAPTURE_GAP_MS = 100


class SoundDeviceRecorder(Recorder):
    """Captures one utterance, gated by a voice-activity detector."""

    def __init__(
        self,
        *,
        vad: Optional[Callable[[np.ndarray], float]] = None,
        frame_source_factory: Optional[Callable[[], Iterable[np.ndarray]]] = None,
        sleep: Optional[Callable[[float], None]] = None,
        sample_rate: int = 16000,
        channels: int = 1,
        frame_size: int = _SILERO_FRAME_SIZE,
        speech_threshold: float = 0.5,
        min_silence_ms: int = 800,
        max_recording_ms: int = 15000,
        pre_roll_ms: int = 300,
        min_speech_ms: int = 250,
    ) -> None:
        self._vad = vad
        self._frame_source_factory = frame_source_factory
        self._sleep = sleep or time.sleep
        self._sample_rate = sample_rate
        self._channels = channels
        self._frame_size = frame_size
        self._speech_threshold = speech_threshold

        frame_ms = frame_size / sample_rate * 1000.0
        self._silence_limit = self._frames_for(min_silence_ms, frame_ms)
        self._max_frames = self._frames_for(max_recording_ms, frame_ms)
        self._pre_roll_frames = self._frames_for(pre_roll_ms, frame_ms)
        self._min_speech_frames = self._frames_for(min_speech_ms, frame_ms)

    def record_until_silence(self) -> AudioBuffer:
        vad = self._loaded_vad()
        # Let the start cue's acoustic tail die before the input stream opens.
        self._sleep(_PRE_CAPTURE_GAP_MS / 1000.0)
        # Keep enough recent frames to recover the onset (pre-roll padding plus
        # the speech-confirmation window) when speech is finally confirmed.
        pre_roll = deque(maxlen=self._pre_roll_frames + self._min_speech_frames)
        collected: list[np.ndarray] = []
        started = False
        silence_run = 0
        speech_run = 0
        total = 0

        for frame in self._frame_source():
            total += 1
            probability = vad(self._to_float32(frame))
            is_speech = probability >= self._speech_threshold

            if not started:
                pre_roll.append(frame)
                if is_speech:
                    speech_run += 1
                    if speech_run >= self._min_speech_frames:
                        started = True
                        collected.extend(pre_roll)
                        pre_roll.clear()
                else:
                    speech_run = 0
            else:
                collected.append(frame)
                if is_speech:
                    silence_run = 0
                else:
                    silence_run += 1
                    if silence_run >= self._silence_limit:
                        break

            if total >= self._max_frames:
                break

        if not started:
            return AudioBuffer.empty()

        pcm = b"".join(np.asarray(f, dtype=np.int16).tobytes() for f in collected)
        return AudioBuffer(
            pcm=pcm,
            sample_rate=self._sample_rate,
            channels=self._channels,
            sample_width=2,
        )

    @staticmethod
    def _frames_for(milliseconds: int, frame_ms: float) -> int:
        return max(1, round(milliseconds / frame_ms))

    def _to_float32(self, frame: np.ndarray) -> np.ndarray:
        return np.asarray(frame, dtype=np.float32) / _INT16_FULL_SCALE

    def _frame_source(self) -> Iterable[np.ndarray]:
        if self._frame_source_factory is not None:
            return self._frame_source_factory()
        return self._default_frame_source()

    def _default_frame_source(self) -> Iterable[np.ndarray]:
        import sounddevice as sd

        with sd.InputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="int16",
            blocksize=self._frame_size,
        ) as stream:
            while True:
                data, _overflowed = stream.read(self._frame_size)
                yield np.asarray(data, dtype=np.int16).reshape(-1)

    def _loaded_vad(self) -> Callable[[np.ndarray], float]:
        if self._vad is None:
            self._vad = self._default_vad()
        return self._vad

    def _default_vad(self) -> Callable[[np.ndarray], float]:
        import torch
        from silero_vad import load_silero_vad

        model = load_silero_vad()

        def _probability(frame: np.ndarray) -> float:
            return float(model(torch.from_numpy(frame), self._sample_rate).item())

        return _probability
