"""HttpPerucaClient: the BrainClient adapter backed by peruca's REST API.

This is the only module aware of the HTTP shape of ``POST /llm/chat`` and of
``httpx``. It translates a domain request into the wire contract and the wire
response back into a :class:`Reply`, never letting ``httpx`` types escape.

Contract (source of truth: ``../peruca`` ``ChatRequest`` / ``ChatResponse``)::

    POST {base_url}/llm/chat
      body:  {"message": str, "external_user_id": str, "chat_id": str}
      reply: {"response": str, "external_user_id": str, "chat_id": str}
"""

from __future__ import annotations

import httpx

from domain.models.conversation import ConversationSession
from domain.models.reply import Reply
from domain.ports.brain_client import BrainClient, BrainUnavailableError

_CHAT_PATH = "/llm/chat"


class HttpPerucaClient(BrainClient):
    """Talks to the peruca brain over HTTP."""

    def __init__(self, base_url: str, timeout_seconds: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def ask(self, message: str, session: ConversationSession) -> Reply:
        payload = {
            "message": message,
            "external_user_id": session.external_user_id,
            "chat_id": session.chat_id,
        }
        try:
            response = httpx.post(
                f"{self._base_url}{_CHAT_PATH}",
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise BrainUnavailableError(
                f"Failed to reach the brain at {self._base_url}{_CHAT_PATH}: {exc}"
            ) from exc

        return Reply(text=data.get("response", ""))
