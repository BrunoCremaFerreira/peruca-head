"""Unit tests for VoiceLoop: the push-to-talk state machine around a turn.

The loop owns IDLE and the repeat; the turn (faked here) owns the inner states.
Also pins the structural anti-echo invariant: the next turn's capture starts only
after the previous turn's playback finished (record/play strictly interleaved).
"""

from application.use_cases.listen import ListenUseCase
from application.use_cases.speak_text import SpeakTextUseCase
from application.use_cases.text_turn import TextTurnUseCase
from application.use_cases.voice_turn import VoiceTurnUseCase
from application.voice_loop import VoiceLoop
from domain.models.audio_buffer import AudioBuffer
from domain.models.conversation import ConversationSession
from domain.models.turn_outcome import TurnOutcome
from domain.models.voice_state import VoiceState
from domain.ports.player import Player
from domain.ports.recorder import Recorder
from tests.fakes.fake_brain_client import FakeBrainClient
from tests.fakes.fake_speaker import FakeSpeaker
from tests.fakes.fake_transcriber import FakeTranscriber


class _FakeTurn:
    def __init__(self):
        self.runs = 0

    def run(self):
        self.runs += 1
        return TurnOutcome.SUCCESS


def _continue_for(n):
    state = {"left": n}

    def _cont():
        if state["left"] <= 0:
            return False
        state["left"] -= 1
        return True

    return _cont


def test_idle_then_trigger_then_turn_for_each_iteration():
    turn = _FakeTurn()
    waits = {"n": 0}
    states: list = []

    loop = VoiceLoop(
        turn,
        wait_for_trigger=lambda: waits.__setitem__("n", waits["n"] + 1),
        should_continue=_continue_for(2),
        on_state=states.append,
    )
    loop.run()

    assert turn.runs == 2
    assert waits["n"] == 2
    # IDLE before each turn plus a final resting IDLE; always ends in IDLE.
    assert states == [VoiceState.IDLE, VoiceState.IDLE, VoiceState.IDLE]
    assert states[-1] is VoiceState.IDLE


def test_no_turn_runs_and_rests_idle_when_should_continue_is_false():
    turn = _FakeTurn()
    states: list = []

    loop = VoiceLoop(
        turn,
        wait_for_trigger=lambda: None,
        should_continue=lambda: False,
        on_state=states.append,
    )
    loop.run()

    assert turn.runs == 0
    assert states == [VoiceState.IDLE]


class _OrderRecorder(Recorder):
    def __init__(self, events):
        self._events = events
        self.buffer = AudioBuffer(pcm=b"\x01\x00", sample_rate=16000, channels=1, sample_width=2)

    def record_until_silence(self):
        self._events.append("record")
        return self.buffer


class _OrderPlayer(Player):
    def __init__(self, events):
        self._events = events

    def play(self, buffer):
        self._events.append("play")


def test_capture_starts_only_after_previous_playback_anti_echo():
    events: list = []
    listen = ListenUseCase(
        recorder=_OrderRecorder(events), transcriber=FakeTranscriber(text="oi")
    )
    text_turn = TextTurnUseCase(
        brain_client=FakeBrainClient(reply_text="resposta"),
        session=ConversationSession("u", "c"),
    )
    speak = SpeakTextUseCase(speaker=FakeSpeaker(), player=_OrderPlayer(events))
    turn = VoiceTurnUseCase(listen=listen, text_turn=text_turn, speak=speak, error_phrase="erro")

    loop = VoiceLoop(
        turn, wait_for_trigger=lambda: None, should_continue=_continue_for(2)
    )
    loop.run()

    # Strict interleave proves each playback completes before the next capture.
    assert events == ["record", "play", "record", "play"]
