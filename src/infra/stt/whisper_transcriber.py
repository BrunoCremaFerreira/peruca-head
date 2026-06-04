"""WhisperTranscriber: the Transcriber adapter backed by faster-whisper.

The only module aware of ``faster_whisper``. It converts the domain
:class:`AudioBuffer` (int16 PCM) into the 16 kHz mono float32 array Whisper
expects (in memory, no .wav on disk) and joins the recognised segments into a
:class:`Transcript`.

``faster_whisper`` is imported lazily and the model is loaded once, so importing
this module needs no model download (tests inject a fake model), and the heavy
``WhisperModel`` construction runs once at startup (composition root), off the
per-turn critical path.

Transcription options are the cientista-validated set: ``language="pt"``,
``condition_on_previous_text=False`` (each turn independent — avoids cross-turn
hallucination), ``vad_filter=False`` (audio is already VAD-trimmed by the
recorder). Empty audio short-circuits to an empty transcript without calling the
model; non-16 kHz / non-mono audio is rejected rather than silently resampled.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from domain.models.audio_buffer import AudioBuffer
from domain.models.transcript import Transcript
from domain.ports.transcriber import Transcriber

_REQUIRED_SAMPLE_RATE = 16000
_REQUIRED_CHANNELS = 1
_INT16_FULL_SCALE = 32768.0


class WhisperTranscriber(Transcriber):
    """Transcribes pt-BR speech with a faster-whisper model."""

    def __init__(
        self,
        model_size: str = "small",
        *,
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "pt",
        beam_size: int = 5,
        model: Optional[Any] = None,
        model_loader: Optional[Any] = None,
    ) -> None:
        """``model`` injects an already-loaded model (tests); ``model_loader`` is
        a ``callable(model_size, device, compute_type) -> model`` overriding how
        the model is built (tests, to avoid importing ``faster_whisper``).
        """
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._beam_size = beam_size
        self._model = model
        self._model_loader = model_loader

    def transcribe(self, audio: AudioBuffer) -> Transcript:
        if audio.is_empty():
            return Transcript(text="")
        self._require_whisper_format(audio)

        samples = np.frombuffer(audio.pcm, dtype=np.int16).astype(np.float32)
        samples /= _INT16_FULL_SCALE

        model = self._loaded_model()
        segments, _info = model.transcribe(
            samples,
            language=self._language,
            beam_size=self._beam_size,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        # faster-whisper already prefixes each segment's text with a space, so we
        # concatenate (joining with a space would double them) and strip the ends.
        text = "".join(segment.text for segment in segments).strip()
        return Transcript(text=text)

    def warm_up(self) -> None:
        """Load the model now and prime it with a short silence, so the first
        real transcription is not slowed by loading / first-inference cost."""
        model = self._loaded_model()
        silence = np.zeros(_REQUIRED_SAMPLE_RATE // 2, dtype=np.float32)  # 0.5 s
        list(model.transcribe(silence, language=self._language)[0])

    @staticmethod
    def _require_whisper_format(audio: AudioBuffer) -> None:
        if audio.sample_rate != _REQUIRED_SAMPLE_RATE:
            raise ValueError(
                f"WhisperTranscriber expects {_REQUIRED_SAMPLE_RATE} Hz audio, "
                f"got {audio.sample_rate} Hz"
            )
        if audio.channels != _REQUIRED_CHANNELS:
            raise ValueError(
                f"WhisperTranscriber expects mono audio, got {audio.channels} channels"
            )

    def _loaded_model(self) -> Any:
        if self._model is None:
            self._model = self._load()
        return self._model

    def _load(self) -> Any:
        if self._model_loader is not None:
            return self._model_loader(self._model_size, self._device, self._compute_type)
        from faster_whisper import WhisperModel

        return WhisperModel(
            self._model_size, device=self._device, compute_type=self._compute_type
        )
