"""Composition root: the only place that knows the concrete adapters.

It reads configuration, instantiates adapters (here just the HTTP brain client),
and wires them into the use case. Use cases see only ports, so swapping an
adapter is a change confined to this module.
"""

from __future__ import annotations

from typing import Callable, Optional

from application.use_cases.check_brain_health import CheckBrainHealthUseCase
from application.use_cases.listen import ListenUseCase
from application.use_cases.speak_text import SpeakTextUseCase
from application.use_cases.text_turn import TextTurnUseCase
from application.use_cases.voice_turn import VoiceTurnUseCase
from application.voice_loop import VoiceLoop
from config import Settings
from domain.models.conversation import ConversationSession
from domain.models.voice_state import VoiceState
from infra.audio.cue_factory import build_start_cue
from infra.audio.sounddevice_player import SoundDevicePlayer
from infra.audio.sounddevice_recorder import SoundDeviceRecorder
from infra.brain.http_peruca_client import HttpPerucaClient
from infra.stt.whisper_transcriber import WhisperTranscriber
from infra.tts.piper_speaker import PiperSpeaker


def build_check_brain_health(settings: Settings) -> CheckBrainHealthUseCase:
    """Wire the startup health probe (short, dedicated timeout)."""
    health_client = HttpPerucaClient(
        base_url=settings.peruca_api_url,
        health_timeout_seconds=settings.health_check_timeout_seconds,
    )
    return CheckBrainHealthUseCase(health_client)


def build_text_turn_use_case(settings: Settings) -> TextTurnUseCase:
    """Wire a :class:`TextTurnUseCase` from configuration."""
    brain_client = HttpPerucaClient(
        base_url=settings.peruca_api_url,
        timeout_seconds=settings.request_timeout_seconds,
    )
    session = ConversationSession(
        external_user_id=settings.external_user_id,
        chat_id=settings.chat_id,
    )
    return TextTurnUseCase(brain_client=brain_client, session=session)


def build_speak_text_use_case(settings: Settings) -> SpeakTextUseCase:
    """Wire a :class:`SpeakTextUseCase` from configuration.

    Loading the Piper voice here (once, at startup) keeps the heavy model off
    the per-turn critical path.
    """
    speaker = PiperSpeaker(
        model_path=settings.piper_voice_path,
        length_scale=settings.piper_length_scale,
    )
    speaker.warm_up()  # pay model loading at startup, not on the first utterance
    player = SoundDevicePlayer()
    return SpeakTextUseCase(speaker=speaker, player=player)


def build_listen_use_case(settings: Settings) -> ListenUseCase:
    """Wire a :class:`ListenUseCase` from configuration.

    Loads the Whisper model once (warm) at startup, off the per-turn path.
    """
    recorder = SoundDeviceRecorder(
        sample_rate=settings.capture_sample_rate,
        frame_size=settings.vad_frame_size,
        speech_threshold=settings.vad_speech_threshold,
        min_silence_ms=settings.vad_min_silence_ms,
        max_recording_ms=settings.vad_max_recording_ms,
        pre_roll_ms=settings.vad_pre_roll_ms,
        min_speech_ms=settings.vad_min_speech_ms,
    )
    transcriber = WhisperTranscriber(
        model_size=settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
        language=settings.stt_language,
        beam_size=settings.whisper_beam_size,
    )
    transcriber.warm_up()
    return ListenUseCase(recorder=recorder, transcriber=transcriber)


def build_voice_loop(
    settings: Settings,
    *,
    wait_for_trigger: Callable[[], object],
    should_continue: Callable[[], bool],
    on_state: Optional[Callable[[VoiceState], None]] = None,
    on_timing: Optional[Callable[[str, float], None]] = None,
) -> VoiceLoop:
    """Wire the full push-to-talk loop (Phase 3).

    Reuses the per-capability builders, so Whisper and Piper are each loaded once
    (warm) here, off the per-turn critical path. The loop and the turn share the
    same ``on_state`` callback (the turn emits LISTENING/THINKING/SPEAKING; the
    loop emits IDLE). The I/O callables come from ``main``.
    """
    start_cue = None
    play_cue = None
    if settings.audio_cues_enabled:
        start_cue = build_start_cue(
            sample_rate=settings.capture_sample_rate,
            freq_hz=settings.start_cue_freq_hz,
            amplitude=settings.start_cue_volume,
        )
        # A dedicated player for the cue; play() opens/closes its stream per call,
        # so it never overlaps the speaker or the recorder (sequential loop).
        play_cue = SoundDevicePlayer().play

    turn = VoiceTurnUseCase(
        listen=build_listen_use_case(settings),
        text_turn=build_text_turn_use_case(settings),
        speak=build_speak_text_use_case(settings),
        error_phrase=settings.error_speech_pt_br,
        on_state=on_state,
        on_timing=on_timing,
        start_cue=start_cue,
        play_cue=play_cue,
    )
    return VoiceLoop(
        turn,
        wait_for_trigger=wait_for_trigger,
        should_continue=should_continue,
        on_state=on_state,
    )
