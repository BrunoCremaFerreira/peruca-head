"""Unit test for main.run_loop's startup guard.

The voice loop (and its spoken error messages) require TTS, so run_loop must
fail fast with a clear message when TTS is not configured — rather than dying in
the Piper warm-up. The guard returns before building any heavy adapter, so this
test needs no model or hardware.
"""

from config import Settings
from main import run_loop


def test_run_loop_requires_tts_configured():
    settings = Settings(_env_file=None, tts_enabled=False, piper_voice_path="")
    outputs: list[str] = []

    run_loop(settings, input_fn=lambda *_a: "", output_fn=outputs.append)

    assert any(
        "tts" in line.lower() or "voice" in line.lower() for line in outputs
    ), outputs
