"""Phase 1 chaining: run_chat speaks the brain's reply when given a speak use case.

Exercises the Phase 0 + Phase 1 chain (typed question -> spoken answer) with all
ports faked: brain, speaker, and player.
"""

from application.use_cases.speak_text import SpeakTextUseCase
from application.use_cases.text_turn import TextTurnUseCase
from domain.models.conversation import ConversationSession
from main import run_chat
from tests.fakes.fake_brain_client import FakeBrainClient
from tests.fakes.fake_player import FakePlayer
from tests.fakes.fake_speaker import FakeSpeaker


def _scripted_input(messages):
    it = iter(messages)

    def _input(_prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    return _input


def test_reply_is_spoken_when_speak_use_case_is_provided():
    brain = FakeBrainClient(reply_text="bom dia para você")
    session = ConversationSession(external_user_id="u", chat_id="c")
    text_turn = TextTurnUseCase(brain_client=brain, session=session)

    speaker = FakeSpeaker()
    player = FakePlayer()
    speak = SpeakTextUseCase(speaker=speaker, player=player)

    run_chat(
        text_turn,
        input_fn=_scripted_input(["bom dia"]),
        output_fn=lambda _line: None,
        speak_use_case=speak,
    )

    assert speaker.texts == ["bom dia para você"]
    assert player.played == [speaker.buffer]


def test_without_speak_use_case_nothing_is_spoken():
    # Backwards-compatible with Phase 0: speaking is optional.
    brain = FakeBrainClient(reply_text="oi")
    session = ConversationSession(external_user_id="u", chat_id="c")
    text_turn = TextTurnUseCase(brain_client=brain, session=session)
    speaker = FakeSpeaker()
    player = FakePlayer()

    run_chat(
        text_turn,
        input_fn=_scripted_input(["oi"]),
        output_fn=lambda _line: None,
    )

    assert player.played == []
    assert speaker.texts == []
