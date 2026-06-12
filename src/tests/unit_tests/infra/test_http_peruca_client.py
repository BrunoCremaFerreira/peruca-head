"""Unit tests for HttpPerucaClient with httpx mocked via respx.

No real network: respx intercepts the httpx transport. These tests pin the wire
contract (request shape, URL) and the translation to/from domain types.
"""

import httpx
import pytest
import respx

from domain.models.conversation import ConversationSession
from domain.ports.brain_client import BrainUnavailableError
from infra.brain.http_peruca_client import HttpPerucaClient

BASE_URL = "http://brain.test:8000"


@pytest.fixture
def session():
    return ConversationSession(external_user_id="user-1", chat_id="chat-1")


@respx.mock
def test_posts_contract_payload_and_returns_reply(session):
    route = respx.post(f"{BASE_URL}/llm/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "response": "olá do cérebro",
                "external_user_id": "user-1",
                "chat_id": "chat-1",
            },
        )
    )
    client = HttpPerucaClient(base_url=BASE_URL)

    reply = client.ask("oi", session)

    assert reply.text == "olá do cérebro"
    assert route.called
    sent = route.calls.last.request
    import json

    assert json.loads(sent.content) == {
        "message": "oi",
        "external_user_id": "user-1",
        "chat_id": "chat-1",
    }


@respx.mock
def test_extracts_text_from_dict_response(session):
    # The peruca routes.py sometimes sets ChatResponse.response = {"output": str}
    # instead of a plain string. The adapter must unwrap it so Reply.text is always str.
    respx.post(f"{BASE_URL}/llm/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "response": {"output": "olá via dict"},
                "external_user_id": "user-1",
                "chat_id": "chat-1",
            },
        )
    )
    client = HttpPerucaClient(base_url=BASE_URL)

    reply = client.ask("oi", session)

    assert reply.text == "olá via dict"


@respx.mock
def test_trailing_slash_in_base_url_does_not_duplicate_path(session):
    route = respx.post(f"{BASE_URL}/llm/chat").mock(
        return_value=httpx.Response(200, json={"response": "ok"})
    )
    client = HttpPerucaClient(base_url=f"{BASE_URL}/")

    client.ask("oi", session)

    assert route.called


@respx.mock
def test_http_error_status_raises_brain_unavailable(session):
    respx.post(f"{BASE_URL}/llm/chat").mock(return_value=httpx.Response(500))
    client = HttpPerucaClient(base_url=BASE_URL)

    with pytest.raises(BrainUnavailableError):
        client.ask("oi", session)


@respx.mock
def test_connection_error_raises_brain_unavailable(session):
    respx.post(f"{BASE_URL}/llm/chat").mock(
        side_effect=httpx.ConnectError("boom")
    )
    client = HttpPerucaClient(base_url=BASE_URL)

    with pytest.raises(BrainUnavailableError):
        client.ask("oi", session)


@respx.mock
def test_check_health_true_when_brain_reports_ok():
    respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    client = HttpPerucaClient(base_url=BASE_URL)

    assert client.check_health() is True


@respx.mock
def test_check_health_false_on_error_status():
    respx.get(f"{BASE_URL}/health").mock(return_value=httpx.Response(503))
    client = HttpPerucaClient(base_url=BASE_URL)

    assert client.check_health() is False


@respx.mock
def test_check_health_false_on_connection_error():
    respx.get(f"{BASE_URL}/health").mock(side_effect=httpx.ConnectError("down"))
    client = HttpPerucaClient(base_url=BASE_URL)

    assert client.check_health() is False


@respx.mock
def test_check_health_false_on_timeout():
    respx.get(f"{BASE_URL}/health").mock(side_effect=httpx.TimeoutException("slow"))
    client = HttpPerucaClient(base_url=BASE_URL)

    assert client.check_health() is False
