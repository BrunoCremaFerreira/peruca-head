"""Opt-in contract test against a real running peruca instance.

Skipped by default. Run explicitly with a peruca on PERUCA_API_URL::

    python -m pytest src/tests/integration_tests -v -m integration

It proves the assumed wire contract still matches the live API end-to-end.
"""

import os

import pytest

from domain.models.conversation import ConversationSession
from infra.brain.http_peruca_client import HttpPerucaClient

pytestmark = pytest.mark.integration


def test_real_brain_answers_a_message():
    base_url = os.environ.get("PERUCA_API_URL", "http://localhost:8000")
    client = HttpPerucaClient(base_url=base_url)
    session = ConversationSession(
        external_user_id="peruca-head-integration-test",
        chat_id="peruca-head-integration-test",
    )

    reply = client.ask("Olá, está me ouvindo?", session)

    assert not reply.is_empty()
