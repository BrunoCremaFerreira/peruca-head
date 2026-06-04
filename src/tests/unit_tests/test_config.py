"""Unit tests for Settings validation (no .env on disk is required)."""

import pytest
from pydantic import ValidationError

from config import Settings


def test_tts_enabled_requires_a_voice_path():
    # Enabling TTS without a voice on disk must fail at startup, not mid-talk.
    with pytest.raises(ValidationError):
        Settings(_env_file=None, tts_enabled=True, piper_voice_path="")


def test_tts_enabled_with_voice_path_is_valid():
    settings = Settings(
        _env_file=None, tts_enabled=True, piper_voice_path="/voices/pt_BR-faber-medium.onnx"
    )
    assert settings.tts_enabled is True
    assert settings.piper_voice_path.endswith(".onnx")


def test_tts_disabled_does_not_require_a_voice_path():
    settings = Settings(_env_file=None, tts_enabled=False, piper_voice_path="")
    assert settings.tts_enabled is False
