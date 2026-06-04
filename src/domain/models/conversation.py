"""ConversationSession: the identity carried with every brain request.

Peruca keeps per-user persistent memory keyed by ``external_user_id`` and groups
a thread of messages by ``chat_id``. This entity holds both so use cases never
have to know how those ids are sourced or persisted.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConversationSession:
    """Stable identity for a conversation with the brain.

    ``external_user_id`` identifies the user (single-user per device for now);
    ``chat_id`` keeps a conversation thread together.
    """

    external_user_id: str
    chat_id: str

    def __post_init__(self) -> None:
        if not self.external_user_id:
            raise ValueError("external_user_id must not be empty")
        if not self.chat_id:
            raise ValueError("chat_id must not be empty")
