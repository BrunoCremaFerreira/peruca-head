"""Single source of configuration, loaded from the environment / ``.env``.

Keeping all knobs here (and out of the adapters) means the composition root can
build warm, fully-configured instances once at startup. See ``.env.example``.
"""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the head, sourced from environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    peruca_api_url: str = "http://localhost:8000"
    external_user_id: str = "peruca-head-device"
    chat_id: str = "peruca-head-session"
    # Voice interactions should not wait ~30s on a stuck brain; ~10s is the
    # tolerance before "this is stuck". Revisit against peruca /llm/chat p95.
    request_timeout_seconds: float = 10.0

    # Spoken (pt-BR) when the brain is unreachable, so a screenless device still
    # signals the failure instead of going silent.
    error_speech_pt_br: str = "Não consegui falar com o cérebro agora."

    # Voice output (TTS). Disabled by default so the text chat runs without a
    # Piper voice on disk; enable once the .onnx voice is in place.
    tts_enabled: bool = False
    piper_voice_path: str = ""  # path to the pt-BR .onnx (its .onnx.json sits beside it)
    piper_length_scale: float = 1.0  # > 1.0 slows speech down

    # Voice input (STT, Phase 2). faster-whisper downloads the model by name, so
    # no path is required. silero-vad drives record-until-silence.
    whisper_model_size: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    stt_language: str = "pt"
    whisper_beam_size: int = 5
    # VAD / capture (silero needs 16 kHz mono; 512-sample frames).
    capture_sample_rate: int = 16000
    vad_frame_size: int = 512
    vad_speech_threshold: float = 0.5
    vad_min_silence_ms: int = 800
    vad_max_recording_ms: int = 15000
    vad_pre_roll_ms: int = 300
    vad_min_speech_ms: int = 250

    @model_validator(mode="after")
    def _voice_path_required_when_tts_enabled(self) -> "Settings":
        if self.tts_enabled and not self.piper_voice_path:
            raise ValueError("piper_voice_path is required when tts_enabled is true")
        return self
