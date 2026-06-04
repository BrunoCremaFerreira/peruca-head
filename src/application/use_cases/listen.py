"""ListenUseCase: capture one utterance and transcribe it.

The Phase 2 vertical slice for voice input: ``Recorder -> Transcriber``. It
depends only on the ports, so neither sounddevice/VAD nor Whisper is visible
here. Silence (an empty buffer) flows through to an empty transcript.
"""

from __future__ import annotations

from domain.models.transcript import Transcript
from domain.ports.recorder import Recorder
from domain.ports.transcriber import Transcriber


class ListenUseCase:
    """Records a single utterance and returns its transcript."""

    def __init__(self, recorder: Recorder, transcriber: Transcriber) -> None:
        self._recorder = recorder
        self._transcriber = transcriber

    def run(self) -> Transcript:
        audio = self._recorder.record_until_silence()
        return self._transcriber.transcribe(audio)
