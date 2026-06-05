"""Unit tests for VoiceTurnUseCase: one full turn record->stt->ask->tts->play.

Built from the real sub-use-cases (Listen/TextTurn/SpeakText) wired to fakes, so
the turn's own logic (state emission, empty short-circuit, brain-error handling,
timing) is exercised against the actual composition.
"""

from dataclasses import dataclass, field

from application.use_cases.listen import ListenUseCase
from application.use_cases.speak_text import SpeakTextUseCase
from application.use_cases.text_turn import TextTurnUseCase
from application.use_cases.voice_turn import VoiceTurnUseCase
from domain.models.audio_buffer import AudioBuffer
from domain.models.conversation import ConversationSession
from domain.models.turn_outcome import TurnOutcome
from domain.models.voice_state import VoiceState
from tests.fakes.fake_brain_client import FakeBrainClient
from tests.fakes.fake_player import FakePlayer
from tests.fakes.fake_recorder import FakeRecorder
from tests.fakes.fake_speaker import FakeSpeaker
from tests.fakes.fake_transcriber import FakeTranscriber

_ERROR_PHRASE = "Não consegui falar com o cérebro agora."


def _counter():
    """A fake monotonic clock: returns 0.0, 1.0, 2.0, ... on each call."""
    state = {"n": 0}

    def _clock() -> float:
        value = float(state["n"])
        state["n"] += 1
        return value

    return _clock


@dataclass
class _Rig:
    turn: VoiceTurnUseCase
    brain: FakeBrainClient
    speaker: FakeSpeaker
    player: FakePlayer
    states: list = field(default_factory=list)
    timings: list = field(default_factory=list)


def _build(
    *,
    transcript_text="ligar a luz da sala",
    reply_text="pronto, liguei",
    raise_brain=False,
    buffer=None,
    clock=None,
):
    recorder = FakeRecorder(buffer=buffer) if buffer is not None else FakeRecorder()
    transcriber = FakeTranscriber(text=transcript_text)
    listen = ListenUseCase(recorder=recorder, transcriber=transcriber)

    brain = FakeBrainClient(reply_text=reply_text, raise_unavailable=raise_brain)
    text_turn = TextTurnUseCase(
        brain_client=brain, session=ConversationSession("user", "chat")
    )

    speaker = FakeSpeaker()
    player = FakePlayer()
    speak = SpeakTextUseCase(speaker=speaker, player=player)

    states: list = []
    timings: list = []
    turn = VoiceTurnUseCase(
        listen=listen,
        text_turn=text_turn,
        speak=speak,
        error_phrase=_ERROR_PHRASE,
        on_state=states.append,
        on_timing=lambda label, seconds: timings.append((label, seconds)),
        clock=clock,
    )
    return _Rig(turn=turn, brain=brain, speaker=speaker, player=player, states=states, timings=timings)


def test_success_path_records_asks_and_speaks_reply():
    rig = _build()

    outcome = rig.turn.run()

    assert outcome is TurnOutcome.SUCCESS
    assert rig.states == [VoiceState.LISTENING, VoiceState.THINKING, VoiceState.SPEAKING]
    assert rig.brain.calls[0].message == "ligar a luz da sala"
    assert rig.speaker.texts == ["pronto, liguei"]
    assert len(rig.player.played) == 1


def test_empty_transcript_short_circuits_before_brain():
    # Silence -> empty buffer -> empty transcript.
    rig = _build(buffer=AudioBuffer.empty())

    outcome = rig.turn.run()

    assert outcome is TurnOutcome.EMPTY
    assert rig.states == [VoiceState.LISTENING]
    assert rig.brain.calls == []
    assert rig.speaker.texts == []


def test_brain_error_speaks_ptbr_error_and_does_not_propagate():
    rig = _build(raise_brain=True)

    outcome = rig.turn.run()

    assert outcome is TurnOutcome.BRAIN_ERROR
    assert rig.states == [VoiceState.LISTENING, VoiceState.THINKING, VoiceState.SPEAKING]
    assert rig.speaker.texts == [_ERROR_PHRASE]
    assert len(rig.player.played) == 1


def test_empty_reply_is_not_played():
    rig = _build(reply_text="")

    outcome = rig.turn.run()

    assert outcome is TurnOutcome.SUCCESS
    assert rig.player.played == []


def test_emits_per_stage_timings_with_brain_isolated():
    rig = _build(clock=_counter())

    rig.turn.run()

    labels = [label for label, _seconds in rig.timings]
    assert labels == ["listen", "brain", "speak"]
