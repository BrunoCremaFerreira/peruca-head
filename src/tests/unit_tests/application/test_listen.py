"""Unit tests for ListenUseCase with Recorder and Transcriber ports faked."""

from application.use_cases.listen import ListenUseCase
from domain.models.audio_buffer import AudioBuffer
from tests.fakes.fake_recorder import FakeRecorder
from tests.fakes.fake_transcriber import FakeTranscriber


def test_records_then_transcribes_and_returns_transcript():
    recorder = FakeRecorder()
    transcriber = FakeTranscriber(text="ligar a luz da sala")
    use_case = ListenUseCase(recorder=recorder, transcriber=transcriber)

    transcript = use_case.run()

    assert transcript.text == "ligar a luz da sala"
    assert recorder.calls == 1
    assert transcriber.received == [recorder.buffer]


def test_silence_yields_empty_transcript():
    recorder = FakeRecorder(buffer=AudioBuffer.empty())
    transcriber = FakeTranscriber(text="should not appear")
    use_case = ListenUseCase(recorder=recorder, transcriber=transcriber)

    transcript = use_case.run()

    assert transcript.is_empty()
