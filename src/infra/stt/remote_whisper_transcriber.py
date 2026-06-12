"""RemoteWhisperTranscriber: Transcriber adapter backed by a remote whisper-asr-webservice.

The only module that knows about the remote ASR HTTP endpoint. It serialises the
domain :class:`AudioBuffer` to WAV bytes using the stdlib (``wave`` + ``io.BytesIO``)
— no external audio library required — and POSTs them to ``{base_url}/asr``.

An :class:`httpx.Client` can be injected for tests; if omitted, the adapter creates
one internally. Network failures (timeout, connection refused) return an empty
:class:`Transcript` rather than propagating, matching the behaviour of
:class:`WhisperTranscriber` on empty audio.

``warm_up()`` is a no-op: there is no local model to load.
"""

from __future__ import annotations

import io
import wave
from typing import Optional

import httpx

from domain.models.audio_buffer import AudioBuffer
from domain.models.transcript import Transcript
from domain.ports.transcriber import Transcriber


class RemoteWhisperTranscriber(Transcriber):
    """Transcribes pt-BR speech via a remote whisper-asr-webservice endpoint."""

    def __init__(
        self,
        base_url: str,
        language: str = "pt",
        timeout_seconds: float = 8.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._base_url = base_url
        self._language = language
        self._timeout = timeout_seconds
        self._client = http_client if http_client is not None else httpx.Client()

    def transcribe(self, audio: AudioBuffer) -> Transcript:
        if audio.is_empty():
            return Transcript(text="")

        wav_bytes = _to_wav(audio)
        try:
            response = self._client.post(
                f"{self._base_url}/asr",
                params={
                    "task": "transcribe",
                    "language": self._language,
                    "output": "json",
                },
                files={"audio_file": ("audio.wav", wav_bytes, "audio/wav")},
                timeout=self._timeout,
            )
            response.raise_for_status()
            text = response.json()["text"].strip()
            return Transcript(text=text)
        except (httpx.TimeoutException, httpx.ConnectError):
            return Transcript(text="")

    def warm_up(self) -> None:
        """No-op: no local model to load."""


def _to_wav(audio: AudioBuffer) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(audio.channels)
        wf.setsampwidth(audio.sample_width)
        wf.setframerate(audio.sample_rate)
        wf.writeframes(audio.pcm)
    return buf.getvalue()
