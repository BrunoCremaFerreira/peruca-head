"""Unit tests for WhisperTranscriber with faster_whisper mocked/injected.

No model is downloaded and `faster_whisper` is never imported: a fake model is
injected. The test pins the int16->float32 conversion, the transcription options
agreed with the cientista, the empty-buffer short-circuit, and the 16k/mono
contract guard.
"""

from dataclasses import dataclass, field

import numpy as np
import pytest

from domain.models.audio_buffer import AudioBuffer
from infra.stt.whisper_transcriber import WhisperTranscriber


@dataclass
class _Segment:
    text: str


@dataclass
class _Info:
    language: str = "pt"


class _FakeModel:
    """Mimics faster_whisper.WhisperModel.transcribe."""

    def __init__(self, segments):
        self._segments = segments
        self.calls: list = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((audio, kwargs))
        return iter(self._segments), _Info()


def _buffer(samples, sample_rate=16000, channels=1):
    pcm = np.asarray(samples, dtype="int16").tobytes()
    return AudioBuffer(pcm=pcm, sample_rate=sample_rate, channels=channels, sample_width=2)


def test_joins_segments_into_transcript_text():
    model = _FakeModel([_Segment(" ligar"), _Segment(" a luz")])
    transcriber = WhisperTranscriber(model_size="small", model=model)

    transcript = transcriber.transcribe(_buffer([1, 2, 3]))

    assert transcript.text == "ligar a luz"


def test_converts_int16_pcm_to_normalized_float32():
    model = _FakeModel([_Segment("oi")])
    transcriber = WhisperTranscriber(model_size="small", model=model)

    transcriber.transcribe(_buffer([0, 16384, -32768]))

    audio, _kwargs = model.calls[0]
    assert audio.dtype == np.float32
    assert np.allclose(audio, np.array([0.0, 16384, -32768], dtype=np.float32) / 32768.0)


def test_passes_agreed_transcription_options():
    model = _FakeModel([_Segment("oi")])
    transcriber = WhisperTranscriber(model_size="small", model=model, language="pt", beam_size=5)

    transcriber.transcribe(_buffer([1, 2]))

    _audio, kwargs = model.calls[0]
    assert kwargs["language"] == "pt"
    assert kwargs["beam_size"] == 5
    assert kwargs["condition_on_previous_text"] is False
    assert kwargs["vad_filter"] is False


def test_empty_buffer_short_circuits_without_calling_model():
    model = _FakeModel([_Segment("should not run")])
    transcriber = WhisperTranscriber(model_size="small", model=model)

    transcript = transcriber.transcribe(AudioBuffer.empty())

    assert transcript.is_empty()
    assert model.calls == []


def test_rejects_non_16k_audio():
    model = _FakeModel([_Segment("oi")])
    transcriber = WhisperTranscriber(model_size="small", model=model)

    with pytest.raises(ValueError):
        transcriber.transcribe(_buffer([1, 2], sample_rate=8000))


def test_rejects_non_mono_audio():
    model = _FakeModel([_Segment("oi")])
    transcriber = WhisperTranscriber(model_size="small", model=model)

    with pytest.raises(ValueError):
        transcriber.transcribe(_buffer([1, 2, 3, 4], channels=2))


def test_warm_up_loads_model_exactly_once():
    loads: list[tuple] = []

    def loader(model_size, device, compute_type):
        loads.append((model_size, device, compute_type))
        return _FakeModel([])

    transcriber = WhisperTranscriber(
        model_size="small", device="cpu", compute_type="int8", model_loader=loader
    )

    transcriber.warm_up()
    transcriber.warm_up()
    transcriber.transcribe(_buffer([1, 2]))

    assert loads == [("small", "cpu", "int8")]
