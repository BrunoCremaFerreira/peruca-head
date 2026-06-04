"""Unit tests for the ConversationSession entity."""

import pytest

from domain.models.conversation import ConversationSession


def test_holds_both_identifiers():
    session = ConversationSession(external_user_id="user-1", chat_id="chat-1")
    assert session.external_user_id == "user-1"
    assert session.chat_id == "chat-1"


def test_is_immutable():
    session = ConversationSession(external_user_id="user-1", chat_id="chat-1")
    with pytest.raises(Exception):
        session.chat_id = "chat-2"  # type: ignore[misc]


def test_equality_is_by_value():
    a = ConversationSession(external_user_id="u", chat_id="c")
    b = ConversationSession(external_user_id="u", chat_id="c")
    assert a == b


@pytest.mark.parametrize(
    "external_user_id,chat_id",
    [("", "chat-1"), ("user-1", "")],
)
def test_rejects_empty_identifiers(external_user_id, chat_id):
    with pytest.raises(ValueError):
        ConversationSession(external_user_id=external_user_id, chat_id=chat_id)
