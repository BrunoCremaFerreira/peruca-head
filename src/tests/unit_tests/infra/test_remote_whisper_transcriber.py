"""Unit tests for RemoteWhisperTranscriber with httpx mocked via injection.

No real HTTP calls are made and no model is loaded: an httpx.Client is injected
with a MagicMock so client.post() is fully controlled. Tests cover the happy
path, edge cases (empty buffer, empty response text), network errors, and the
no-op warm_up.
"""

import numpy as np
import pytest
import httpx
from unittest.mock import MagicMock, call

from domain.models.audio_buffer import AudioBuffer
from domain.models.transcript import Transcript
from infra.stt.remote_whisper_transcriber import RemoteWhisperTranscriber


def _audio_buffer(samples=(100, 200, 300), sample_rate=16000):
    pcm = np.array(samples, dtype=np.int16).tobytes()
    return AudioBuffer(pcm=pcm, sample_rate=sample_rate, channels=1, sample_width=2)


def _make_client(json_payload):
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock()
    mock_response.json.return_value = json_payload
    mock_client.post.return_value = mock_response
    return mock_client


def test_transcribes_speech_from_json_response():
    client = _make_client({"text": " oi mundo"})
    transcriber = RemoteWhisperTranscriber(
        base_url="http://localhost:9000", http_client=client
    )

    result = transcriber.transcribe(_audio_buffer())

    assert result == Transcript("oi mundo")


def test_empty_json_text_yields_empty_transcript():
    client = _make_client({"text": ""})
    transcriber = RemoteWhisperTranscriber(
        base_url="http://localhost:9000", http_client=client
    )

    result = transcriber.transcribe(_audio_buffer())

    assert result == Transcript("")
    assert result.is_empty() is True


def test_empty_audio_buffer_short_circuits_without_http_call():
    client = _make_client({"text": "should not be called"})
    transcriber = RemoteWhisperTranscriber(
        base_url="http://localhost:9000", http_client=client
    )

    result = transcriber.transcribe(AudioBuffer.empty())

    assert result.is_empty() is True
    client.post.assert_not_called()


def test_sends_wav_as_multipart_audio_file():
    client = _make_client({"text": "oi"})
    transcriber = RemoteWhisperTranscriber(
        base_url="http://localhost:9000", http_client=client
    )

    transcriber.transcribe(_audio_buffer())

    assert client.post.call_count == 1
    _args, kwargs = client.post.call_args
    files = kwargs.get("files") or _args[1] if len(_args) > 1 else kwargs["files"]
    assert "audio_file" in files
    audio_file_entry = files["audio_file"]
    # entry is a tuple: (filename, bytes, content_type) or (filename, bytes)
    assert isinstance(audio_file_entry, tuple)
    assert isinstance(audio_file_entry[1], bytes)


def test_sends_correct_query_params():
    client = _make_client({"text": "oi"})
    transcriber = RemoteWhisperTranscriber(
        base_url="http://localhost:9000", language="pt", http_client=client
    )

    transcriber.transcribe(_audio_buffer())

    _args, kwargs = client.post.call_args
    params = kwargs.get("params") or {}
    assert params.get("task") == "transcribe"
    assert params.get("language") == "pt"
    assert params.get("output") == "json"


def test_timeout_exception_yields_empty_transcript():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.TimeoutException("timed out")
    transcriber = RemoteWhisperTranscriber(
        base_url="http://localhost:9000", http_client=mock_client
    )

    result = transcriber.transcribe(_audio_buffer())

    assert result.is_empty() is True


def test_connect_error_yields_empty_transcript():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ConnectError("refused")
    transcriber = RemoteWhisperTranscriber(
        base_url="http://localhost:9000", http_client=mock_client
    )

    result = transcriber.transcribe(_audio_buffer())

    assert result.is_empty() is True


def test_warm_up_is_noop_and_does_not_call_http():
    client = _make_client({"text": "should not be called"})
    transcriber = RemoteWhisperTranscriber(
        base_url="http://localhost:9000", http_client=client
    )

    transcriber.warm_up()

    client.post.assert_not_called()
