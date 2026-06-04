"""In-memory fake of the BrainClient port for use across unit tests.

It records every call and returns a canned reply, so use cases and the CLI loop
can be exercised without HTTP, a model, or a running peruca instance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.conversation import ConversationSession
from domain.models.reply import Reply
from domain.ports.brain_client import BrainClient, BrainUnavailableError


@dataclass
class _Call:
    message: str
    session: ConversationSession


@dataclass
class FakeBrainClient(BrainClient):
    """A scriptable BrainClient.

    - ``reply_text`` is echoed back as the reply for every ``ask``.
    - set ``raise_unavailable=True`` to simulate the brain being down.
    - ``calls`` records each invocation for assertions.
    """

    reply_text: str = "ok"
    raise_unavailable: bool = False
    calls: list[_Call] = field(default_factory=list)

    def ask(self, message: str, session: ConversationSession) -> Reply:
        self.calls.append(_Call(message=message, session=session))
        if self.raise_unavailable:
            raise BrainUnavailableError("fake brain is unavailable")
        return Reply(text=self.reply_text)
