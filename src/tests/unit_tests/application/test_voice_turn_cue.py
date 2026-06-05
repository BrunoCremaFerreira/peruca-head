"""Unit tests for the start-cue orchestration in VoiceTurnUseCase.

The cue (a prebuilt AudioBuffer) is played via the injected ``play_cue`` callable
right after entering LISTENING and BEFORE capture, so it cannot leak into the
recording. When no cue is configured, nothing is played.
"""

from application.use_cases.listen import ListenUseCase
from application.use_cases.speak_text import SpeakTextUseCase
from application.use_cases.text_turn import TextTurnUseCase
from application.use_cases.voice_turn import VoiceTurnUseCase
from domain.models.audio_buffer import AudioBuffer
from domain.models.conversation import ConversationSession
from domain.ports.recorder import Recorder
from tests.fakes.fake_brain_client import FakeBrainClient
from tests.fakes.fake_player import FakePlayer
from tests.fakes.fake_speaker import FakeSpeaker
from tests.fakes.fake_transcriber import FakeTranscriber

_CUE = AudioBuffer(pcm=b"\x10\x00\x20\x00", sample_rate=16000, channels=1, sample_width=2)


class _OrderRecorder(Recorder):
    def __init__(self, events):
        self._events = events
        self.buffer = AudioBuffer(pcm=b"\x01\x00", sample_rate=16000, channels=1, sample_width=2)

    def record_until_silence(self):
        self._events.append("record")
        return self.buffer


def _turn(events, *, start_cue=None, play_cue=None):
    listen = ListenUseCase(
        recorder=_OrderRecorder(events), transcriber=FakeTranscriber(text="oi")
    )
    text_turn = TextTurnUseCase(
        brain_client=FakeBrainClient(reply_text="ok"),
        session=ConversationSession("u", "c"),
    )
    speak = SpeakTextUseCase(speaker=FakeSpeaker(), player=FakePlayer())
    return VoiceTurnUseCase(
        listen=listen,
        text_turn=text_turn,
        speak=speak,
        error_phrase="erro",
        start_cue=start_cue,
        play_cue=play_cue,
    )


def test_cue_is_played_before_capture():
    events: list = []
    turn = _turn(events, start_cue=_CUE, play_cue=lambda buf: events.append(("cue", buf)))

    turn.run()

    assert events[0] == ("cue", _CUE)
    assert events[1] == "record"


def test_no_cue_when_not_configured():
    events: list = []
    turn = _turn(events)  # no start_cue / play_cue

    turn.run()

    assert events == ["record"]
