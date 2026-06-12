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


def test_request_timeout_default_is_voice_friendly():
    # Phase 3: 30s is too long to wait on a voice interaction; default is 10s.
    assert Settings(_env_file=None).request_timeout_seconds == 10.0


def test_has_a_ptbr_brain_error_phrase():
    phrase = Settings(_env_file=None).error_speech_pt_br
    assert isinstance(phrase, str) and phrase.strip() != ""


def test_phase4_knobs_have_daily_use_defaults():
    settings = Settings(_env_file=None)
    assert settings.log_level == "INFO"
    assert settings.audio_cues_enabled is True
    assert settings.start_cue_freq_hz == 880.0
    assert settings.start_cue_volume == 0.3
    assert settings.health_check_enabled is True
    # Dedicated short timeout, distinct from the 10s per-turn request timeout.
    assert settings.health_check_timeout_seconds == 2.0
    assert settings.health_check_timeout_seconds < settings.request_timeout_seconds


def test_trigger_defaults_to_push_to_talk():
    settings = Settings(_env_file=None)
    assert settings.trigger_type == "enter"
    assert settings.wake_word_frame_size == 1280  # not the silero 512
    assert settings.wake_word_threshold == 0.5
    assert settings.vad_pre_capture_gap_enter_ms == 100
    assert settings.vad_pre_capture_gap_wakeword_ms == 40


def test_wake_word_requires_a_model_path():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, trigger_type="wake_word", wake_word_model_path="")


def test_wake_word_with_model_path_is_valid():
    settings = Settings(
        _env_file=None, trigger_type="wake_word", wake_word_model_path="/m/peruca.onnx"
    )
    assert settings.trigger_type == "wake_word"


def test_rejects_unknown_trigger_type():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, trigger_type="telepathy")


def test_vosk_requires_model_path():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, trigger_type="vosk", vosk_model_path="")


def test_vosk_with_model_path_is_valid():
    settings = Settings(
        _env_file=None, trigger_type="vosk", vosk_model_path="/models/vosk-model-small-pt-0.3"
    )
    assert settings.trigger_type == "vosk"
    assert settings.vosk_keyword == "peruca"
    assert settings.vosk_frame_size == 4000


def test_stt_defaults_to_local_mode():
    assert Settings(_env_file=None).stt_mode == "local"


def test_remote_stt_requires_url():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, stt_mode="remote", remote_stt_url="")


def test_remote_stt_with_url_is_valid():
    settings = Settings(
        _env_file=None, stt_mode="remote", remote_stt_url="http://192.168.1.100:9000"
    )
    assert settings.stt_mode == "remote"
    assert settings.remote_stt_url == "http://192.168.1.100:9000"


def test_local_stt_does_not_require_url():
    settings = Settings(_env_file=None, stt_mode="local", remote_stt_url="")
    assert settings.stt_mode == "local"


def test_unknown_stt_mode_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, stt_mode="cloud")
