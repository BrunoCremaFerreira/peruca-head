"""Unit tests for TextTurnUseCase with the BrainClient port faked."""

import pytest

from application.use_cases.text_turn import TextTurnUseCase
from domain.models.conversation import ConversationSession
from tests.fakes.fake_brain_client import FakeBrainClient


@pytest.fixture
def session():
    return ConversationSession(external_user_id="user-1", chat_id="chat-1")


def test_forwards_message_to_brain_and_returns_reply(session):
    brain = FakeBrainClient(reply_text="oi, tudo bem?")
    use_case = TextTurnUseCase(brain_client=brain, session=session)

    reply = use_case.run("olá")

    assert reply.text == "oi, tudo bem?"
    assert len(brain.calls) == 1
    assert brain.calls[0].message == "olá"
    assert brain.calls[0].session == session


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_blank_message_is_a_noop_and_does_not_call_brain(session, blank):
    brain = FakeBrainClient(reply_text="should not be returned")
    use_case = TextTurnUseCase(brain_client=brain, session=session)

    reply = use_case.run(blank)

    assert reply.is_empty()
    assert brain.calls == []


def test_propagates_brain_unavailable(session):
    from domain.ports.brain_client import BrainUnavailableError

    brain = FakeBrainClient(raise_unavailable=True)
    use_case = TextTurnUseCase(brain_client=brain, session=session)

    with pytest.raises(BrainUnavailableError):
        use_case.run("olá")
