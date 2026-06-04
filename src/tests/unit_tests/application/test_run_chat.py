"""Unit tests for the terminal chat loop (main.run_chat) with injected I/O."""

from application.use_cases.text_turn import TextTurnUseCase
from domain.models.conversation import ConversationSession
from main import run_chat
from tests.fakes.fake_brain_client import FakeBrainClient


def _use_case(brain: FakeBrainClient) -> TextTurnUseCase:
    session = ConversationSession(external_user_id="user-1", chat_id="chat-1")
    return TextTurnUseCase(brain_client=brain, session=session)


def _scripted_input(messages):
    """Return an input_fn that yields each message then raises EOFError."""
    it = iter(messages)

    def _input(_prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    return _input


def test_prints_brain_reply_for_a_message():
    brain = FakeBrainClient(reply_text="resposta da peruca")
    outputs: list[str] = []

    run_chat(
        _use_case(brain),
        input_fn=_scripted_input(["bom dia"]),
        output_fn=outputs.append,
    )

    assert any("resposta da peruca" in line for line in outputs)
    assert brain.calls[0].message == "bom dia"


def test_exit_command_stops_loop_without_calling_brain():
    brain = FakeBrainClient()
    outputs: list[str] = []

    run_chat(
        _use_case(brain),
        input_fn=_scripted_input(["exit", "bom dia"]),
        output_fn=outputs.append,
    )

    assert brain.calls == []


def test_brain_error_is_reported_and_loop_continues():
    brain = FakeBrainClient(raise_unavailable=True)
    outputs: list[str] = []

    run_chat(
        _use_case(brain),
        input_fn=_scripted_input(["bom dia", "boa tarde"]),
        output_fn=outputs.append,
    )

    error_lines = [line for line in outputs if line.startswith("[error]")]
    assert len(error_lines) == 2  # both turns attempted, neither crashed the loop
