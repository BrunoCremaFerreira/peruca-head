"""Opt-in contract test against a real running whisper-asr-webservice instance.

Skipped by default. Run with the server reachable on REMOTE_STT_URL:

    python -m pytest src/tests/integration_tests/test_remote_whisper_contract.py -v -m integration

To generate the audio fixture (requires TTS enabled and PIPER_VOICE_PATH set):

    python scripts/generate_stt_fixture.py
"""

import os
import wave
from pathlib import Path

import numpy as np
import pytest

from domain.models.audio_buffer import AudioBuffer
from infra.stt.remote_whisper_transcriber import RemoteWhisperTranscriber

pytestmark = pytest.mark.integration

REMOTE_STT_URL = os.environ.get("REMOTE_STT_URL", "http://unix.rtx-server:9000")
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ola_peruca.wav"


def _silence_buffer(duration_s: float = 0.5) -> AudioBuffer:
    samples = np.zeros(int(16000 * duration_s), dtype=np.int16)
    return AudioBuffer(pcm=samples.tobytes(), sample_rate=16000, channels=1, sample_width=2)


def _load_wav(path: Path) -> AudioBuffer:
    with wave.open(str(path), "rb") as wf:
        return AudioBuffer(
            pcm=wf.readframes(wf.getnframes()),
            sample_rate=wf.getframerate(),
            channels=wf.getnchannels(),
            sample_width=wf.getsampwidth(),
        )


def test_server_is_reachable():
    """The whisper-asr-webservice responds to a real request without network error."""
    transcriber = RemoteWhisperTranscriber(base_url=REMOTE_STT_URL, timeout_seconds=15.0)

    result = transcriber.transcribe(_silence_buffer(0.5))

    # Silence may return empty text or a hallucination — only connectivity matters here.
    assert isinstance(result.text, str)


def test_transcribes_known_pt_br_phrase():
    """'olá peruca' (WAV fixture) is correctly recognised by the remote model."""
    if not FIXTURE_PATH.exists():
        pytest.skip(
            f"Fixture not found: {FIXTURE_PATH}. "
            "Run `python scripts/generate_stt_fixture.py` to generate it."
        )

    transcriber = RemoteWhisperTranscriber(base_url=REMOTE_STT_URL, timeout_seconds=15.0)

    result = transcriber.transcribe(_load_wav(FIXTURE_PATH))

    assert not result.is_empty(), f"Expected transcription, got empty. Server: {REMOTE_STT_URL}"
    assert "peruca" in result.text.lower(), (
        f"Expected 'peruca' in transcription, got: {result.text!r}"
    )


def test_unreachable_server_returns_empty_transcript():
    """When the server is unreachable, the voice loop must not crash."""
    transcriber = RemoteWhisperTranscriber(
        base_url="http://localhost:19999",
        timeout_seconds=2.0,
    )

    result = transcriber.transcribe(_silence_buffer(0.5))

    assert result.is_empty()
