"""CLI entrypoint: a text chat in the terminal against the peruca brain.

Phase 0 deliverable: type a message, see peruca's reply. No audio yet. Run with
the ``peruca-head`` console script or ``python src/main.py``.
"""

from __future__ import annotations

import sys

from application.use_cases.listen import ListenUseCase
from application.use_cases.speak_text import SpeakTextUseCase
from application.use_cases.text_turn import TextTurnUseCase
from composition import (
    build_listen_use_case,
    build_speak_text_use_case,
    build_text_turn_use_case,
    build_voice_loop,
)
from config import Settings
from domain.models.voice_state import VoiceState
from domain.ports.brain_client import BrainUnavailableError

_EXIT_COMMANDS = {"exit", "quit", "sair"}


def run_chat(
    use_case: TextTurnUseCase,
    *,
    input_fn=input,
    output_fn=print,
    speak_use_case: SpeakTextUseCase | None = None,
) -> None:
    """Run the interactive text loop until the user exits or sends EOF.

    ``input_fn`` / ``output_fn`` are injected so the loop is testable without a
    real terminal. When ``speak_use_case`` is given, each non-empty reply is also
    spoken (Phase 1); when omitted, the loop stays text-only (Phase 0).
    """
    output_fn("peruca-head (text mode). Type 'exit' to quit.")
    while True:
        try:
            message = input_fn("you> ")
        except EOFError:
            output_fn("")
            return

        if message.strip().lower() in _EXIT_COMMANDS:
            return

        try:
            reply = use_case.run(message)
        except BrainUnavailableError as exc:
            output_fn(f"[error] {exc}")
            continue

        if not reply.is_empty():
            output_fn(f"peruca> {reply.text}")
            if speak_use_case is not None:
                speak_use_case.run(reply.text)


def run_listen(
    use_case: ListenUseCase,
    *,
    output_fn=print,
    should_continue=lambda: True,
) -> None:
    """Phase 2 deliverable: record an utterance, print the recognised text, repeat.

    ``should_continue`` is injected so the loop is testable; in real use it stays
    ``True`` and the loop is ended with Ctrl-C.
    """
    output_fn("peruca-head (listen mode). Speak; Ctrl-C to stop.")
    while should_continue():
        output_fn("listening…")
        transcript = use_case.run()
        if not transcript.is_empty():
            output_fn(f"you said> {transcript.text}")


def run_loop(settings: Settings, *, input_fn=input, output_fn=print) -> None:
    """Phase 3 deliverable: full push-to-talk voice conversation.

    Press Enter, speak, hear peruca's reply, repeat. Console shows the loop state
    and per-stage timings (brain latency isolated). Ctrl-C / EOF ends the loop.
    """
    if not settings.tts_enabled or not settings.piper_voice_path:
        output_fn(
            "The voice loop needs TTS configured (replies and errors are spoken). "
            "Set TTS_ENABLED=true and PIPER_VOICE_PATH in .env."
        )
        return

    def on_state(state: VoiceState) -> None:
        output_fn(f"[{state.name.lower()}]")

    def on_timing(label: str, seconds: float) -> None:
        output_fn(f"  · {label}: {seconds:.2f}s")

    loop = build_voice_loop(
        settings,
        wait_for_trigger=lambda: input_fn("press Enter and speak… "),
        should_continue=lambda: True,
        on_state=on_state,
        on_timing=on_timing,
    )
    output_fn("peruca-head (voice loop). Press Enter to talk; Ctrl-C to stop.")
    try:
        loop.run()
    except (EOFError, KeyboardInterrupt):
        output_fn("\nbye")


def main() -> None:
    settings = Settings()
    mode = sys.argv[1:2]
    if mode == ["listen"]:
        run_listen(build_listen_use_case(settings))
        return
    if mode == ["loop"]:
        run_loop(settings)
        return
    text_turn = build_text_turn_use_case(settings)
    speak = build_speak_text_use_case(settings) if settings.tts_enabled else None
    run_chat(text_turn, speak_use_case=speak)


if __name__ == "__main__":
    main()
