"""VoskTrigger: always-on keyword detection via Vosk (pt-BR, no model training).

The only module aware of ``vosk``. Reads 16 kHz mono int16 frames and returns from
:meth:`wait_for_trigger` as soon as the keyword is recognised in a Vosk result,
then closes the input stream — mic contention resolved identically to
``WakeWordTrigger`` (sequential single-threaded loop + blocking playback).

Heavy collaborators are injectable and lazily built:
- ``recognizer``: ``Callable[[np.ndarray], bool]`` — True when the keyword is
  detected in the frame.  Default: a ``KaldiRecognizer`` with a 2-word grammar
  ``[keyword, "[unk]"]`` so the decoder computes only over the target vocabulary.
- ``frame_source_factory``: ``Callable[[], Iterable[int16 ndarray]]`` — default
  opens a sounddevice InputStream.

Vosk accepts raw int16 bytes (``frame.tobytes()``); frame_size of 4000 samples
(250 ms @ 16 kHz) is the recommended chunk size — different from openWakeWord's
1280 and silero's 512.  Detection happens only on utterance boundaries
(``AcceptWaveform`` returns True), so ``PartialResult`` is intentionally ignored.
"""

from __future__ import annotations

import json
from typing import Callable, Iterable, Optional

import numpy as np

from domain.ports.trigger import Trigger


class VoskTrigger(Trigger):
    """Blocks until the configured keyword is recognised by Vosk."""

    def __init__(
        self,
        model_path: str,
        keyword: str = "peruca",
        *,
        recognizer: Optional[Callable[[np.ndarray], bool]] = None,
        frame_source_factory: Optional[Callable[[], Iterable[np.ndarray]]] = None,
        sample_rate: int = 16000,
        frame_size: int = 4000,
    ) -> None:
        self._model_path = model_path
        self._keyword = keyword.strip().lower()
        self._recognizer = recognizer
        self._frame_source_factory = frame_source_factory
        self._sample_rate = sample_rate
        self._frame_size = frame_size

    def wait_for_trigger(self) -> None:
        rec = self._loaded_recognizer()
        source = self._frame_source()
        try:
            for frame in source:
                if rec(frame):
                    return
        finally:
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

    def _loaded_recognizer(self) -> Callable[[np.ndarray], bool]:
        if self._recognizer is None:
            self._recognizer = self._default_recognizer()
        return self._recognizer

    def _default_recognizer(self) -> Callable[[np.ndarray], bool]:
        from vosk import KaldiRecognizer, Model

        grammar = json.dumps([self._keyword, "[unk]"])
        model = Model(self._model_path)
        rec = KaldiRecognizer(model, self._sample_rate, grammar)
        keyword = self._keyword

        def _recognize(frame: np.ndarray) -> bool:
            if rec.AcceptWaveform(frame.tobytes()):
                result = json.loads(rec.Result())
                return keyword in result.get("text", "").strip().lower()
            return False

        return _recognize
