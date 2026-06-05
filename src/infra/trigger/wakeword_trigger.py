"""WakeWordTrigger: always-on keyword detection via openWakeWord.

The only module aware of ``openwakeword``. It reads 16 kHz mono int16 frames and
returns from :meth:`wait_for_trigger` as soon as the wake-word score crosses the
threshold, then closes its input stream — so it never holds the microphone while
the recorder captures the turn (mic contention is resolved structurally by the
sequential, single-threaded loop with blocking playback).

Both heavy collaborators are injectable and lazily built (mirroring
``SoundDeviceRecorder``), so the module imports and unit-tests with no mic, no
openWakeWord, and no model:
- ``detector``: ``callable(int16_frame) -> score``; by default an openWakeWord
  model loaded lazily.
- ``frame_source_factory``: ``callable() -> Iterable[int16 ndarray]`` yielding
  1280-sample (80 ms) frames; by default a sounddevice input stream.

openWakeWord requires 1280-sample frames at 16 kHz (do not reuse silero's 512).
``refractory_s`` is reserved for a future concurrent/barge-in mode; the sequential
v1 returns on the first detection (the turn itself is the refractory), so it is
not exercised here.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

import numpy as np

from domain.ports.trigger import Trigger

_WAKEWORD_FRAME_SIZE = 1280  # openWakeWord: 80 ms at 16 kHz


class WakeWordTrigger(Trigger):
    """Blocks until the wake word is detected."""

    def __init__(
        self,
        model_path: str,
        *,
        detector: Optional[Callable[[np.ndarray], float]] = None,
        frame_source_factory: Optional[Callable[[], Iterable[np.ndarray]]] = None,
        sample_rate: int = 16000,
        frame_size: int = _WAKEWORD_FRAME_SIZE,
        threshold: float = 0.5,
        refractory_s: float = 2.0,
    ) -> None:
        self._model_path = model_path
        self._detector = detector
        self._frame_source_factory = frame_source_factory
        self._sample_rate = sample_rate
        self._frame_size = frame_size
        self._threshold = threshold
        self._refractory_s = refractory_s

    def wait_for_trigger(self) -> None:
        detector = self._loaded_detector()
        source = self._frame_source()
        try:
            for frame in source:
                if detector(frame) >= self._threshold:
                    return
        finally:
            # Close deterministically so PortAudio releases the device before the
            # recorder opens it (don't rely on GC).
            close = getattr(source, "close", None)
            if callable(close):
                close()

    def _frame_source(self) -> Iterable[np.ndarray]:
        if self._frame_source_factory is not None:
            return self._frame_source_factory()
        return self._default_frame_source()

    def _default_frame_source(self):
        import sounddevice as sd

        stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self._frame_size,
        )
        stream.start()

        def _frames():
            try:
                while True:
                    data, _overflowed = stream.read(self._frame_size)
                    yield np.asarray(data, dtype=np.int16).reshape(-1)
            finally:
                stream.stop()
                stream.close()

        return _frames()

    def _loaded_detector(self) -> Callable[[np.ndarray], float]:
        if self._detector is None:
            self._detector = self._default_detector()
        return self._detector

    def _default_detector(self) -> Callable[[np.ndarray], float]:
        from openwakeword.model import Model

        model = Model(wakeword_models=[self._model_path], inference_framework="onnx")

        def _score(frame: np.ndarray) -> float:
            predictions = model.predict(frame)
            return float(max(predictions.values())) if predictions else 0.0

        return _score
