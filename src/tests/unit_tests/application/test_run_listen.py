"""Unit tests for the listen loop (main.run_listen) with ports faked."""

from application.use_cases.listen import ListenUseCase
from domain.models.audio_buffer import AudioBuffer
from main import run_listen
from tests.fakes.fake_recorder import FakeRecorder
from tests.fakes.fake_transcriber import FakeTranscriber


def _continue_for(n):
    """A should_continue callable that returns True n times, then False."""
    state = {"left": n}

    def _cont():
        if state["left"] <= 0:
            return False
        state["left"] -= 1
        return True

    return _cont


def test_prints_each_recognized_phrase():
    recorder = FakeRecorder()
    transcriber = FakeTranscriber(text="apague a luz")
    use_case = ListenUseCase(recorder=recorder, transcriber=transcriber)
    outputs: list[str] = []

    run_listen(use_case, output_fn=outputs.append, should_continue=_continue_for(2))

    spoken = [line for line in outputs if "apague a luz" in line]
    assert len(spoken) == 2
    assert recorder.calls == 2


def test_empty_transcript_is_not_printed():
    recorder = FakeRecorder(buffer=AudioBuffer.empty())
    transcriber = FakeTranscriber()
    use_case = ListenUseCase(recorder=recorder, transcriber=transcriber)
    outputs: list[str] = []

    run_listen(use_case, output_fn=outputs.append, should_continue=_continue_for(1))

    # Nothing recognized -> no "you said" line (only the optional banner/listening cue).
    assert not any("you said" in line.lower() for line in outputs)
