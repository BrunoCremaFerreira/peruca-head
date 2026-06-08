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

    # --- Robustness & feedback (Phase 4) ---
    log_level: str = "INFO"
    # Start cue: a short beep meaning "you can speak", played before capture.
    audio_cues_enabled: bool = True
    start_cue_freq_hz: float = 880.0
    start_cue_volume: float = 0.3  # fraction of full scale (headroom vs saturation)
    # /health probe at startup (warn-and-continue). Short, dedicated timeout so a
    # down brain never hangs the boot.
    health_check_enabled: bool = True
    health_check_timeout_seconds: float = 2.0

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
    # Silence before opening the input stream so the start cue's tail dies first.
    # Wake-word mode uses a smaller gap (the wake detection already paced things);
    # the composition root picks the value per trigger_type.
    vad_pre_capture_gap_enter_ms: int = 100
    vad_pre_capture_gap_wakeword_ms: int = 40

    # --- Trigger / wake word (Phase 5) ---
    # "enter" = push-to-talk (default; reliable, no model needed).
    # "wake_word" = always-on keyword detection (needs wake_word_model_path).
    trigger_type: str = "enter"
    wake_word_model_path: str = ""  # openWakeWord .onnx (stock models are English)
    wake_word_threshold: float = 0.5
    wake_word_refractory_s: float = 2.0  # reserved; not exercised by the sequential v1
    wake_word_frame_size: int = 1280  # openWakeWord needs 1280 (not silero's 512)
    # Vosk keyword trigger (pt-BR, no model training required).
    # vosk_model_path must point to the extracted model directory (not a zip).
    vosk_model_path: str = ""
    vosk_frame_size: int = 4000  # 250 ms @ 16 kHz (Vosk range: 2000–8000)
    vosk_keyword: str = "peruca"

    @model_validator(mode="after")
    def _voice_path_required_when_tts_enabled(self) -> "Settings":
        if self.tts_enabled and not self.piper_voice_path:
            raise ValueError("piper_voice_path is required when tts_enabled is true")
        return self

    @model_validator(mode="after")
    def _validate_trigger(self) -> "Settings":
        if self.trigger_type not in {"enter", "wake_word", "vosk"}:
            raise ValueError("trigger_type must be 'enter', 'wake_word', or 'vosk'")
        if self.trigger_type == "wake_word" and not self.wake_word_model_path:
            raise ValueError(
                "wake_word_model_path is required when trigger_type is 'wake_word'"
            )
        if self.trigger_type == "vosk" and not self.vosk_model_path:
            raise ValueError(
                "vosk_model_path is required when trigger_type is 'vosk'"
            )
        return self
