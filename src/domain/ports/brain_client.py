"""BrainClient port: the contract for talking to the Peruca brain.

The port speaks only in domain types (``str`` message in, :class:`Reply` out,
:class:`ConversationSession` for identity). No HTTP, no library types leak
through it, so the orchestration layer stays decoupled from how the brain is
reached.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.conversation import ConversationSession
from domain.models.reply import Reply


class BrainClient(ABC):
    """Sends a user message to the brain and returns its reply."""

    @abstractmethod
    def ask(self, message: str, session: ConversationSession) -> Reply:
        """Ask the brain ``message`` within ``session`` and return its reply.

        Raises:
            BrainUnavailableError: when the brain cannot be reached or fails.
        """
        raise NotImplementedError


class BrainUnavailableError(Exception):
    """Raised when the brain cannot be reached or returns an error."""
