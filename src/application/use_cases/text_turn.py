"""TextTurnUseCase: one text-only turn of the conversation.

This is the Phase 0 vertical slice that proves the brain integration:
``message text -> brain -> reply text``. Later phases wrap audio around it
(record -> STT -> this -> TTS -> play), but the orchestration seam is already
here: the use case depends only on the :class:`BrainClient` port.
"""

from __future__ import annotations

from domain.models.conversation import ConversationSession
from domain.models.reply import Reply
from domain.ports.brain_client import BrainClient


class TextTurnUseCase:
    """Runs a single text turn against the brain within a fixed session."""

    def __init__(self, brain_client: BrainClient, session: ConversationSession) -> None:
        self._brain_client = brain_client
        self._session = session

    def run(self, message: str) -> Reply:
        """Send ``message`` to the brain and return its reply.

        An empty/whitespace-only message is a no-op turn: it returns an empty
        :class:`Reply` without bothering the brain.
        """
        if message.strip() == "":
            return Reply(text="")
        return self._brain_client.ask(message, self._session)
