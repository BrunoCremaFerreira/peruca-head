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
from domain.ports.trigger import Trigger
from infra.audio.cue_factory import build_start_cue
from infra.audio.sounddevice_player import SoundDevicePlayer
from infra.audio.sounddevice_recorder import SoundDeviceRecorder
from infra.brain.http_peruca_client import HttpPerucaClient
from infra.stt.remote_whisper_transcriber import RemoteWhisperTranscriber
from infra.stt.whisper_transcriber import WhisperTranscriber
from infra.trigger.enter_trigger import EnterTrigger
from infra.trigger.vosk_trigger import VoskTrigger
from infra.trigger.wakeword_trigger import WakeWordTrigger
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
    # The pre-capture gap depends on the trigger: wake word needs only a short
    # settle, push-to-talk waits out the full cue tail. The recorder stays
    # trigger-agnostic — it just receives the chosen number.
    pre_capture_gap_ms = (
        settings.vad_pre_capture_gap_wakeword_ms
        if settings.trigger_type in {"wake_word", "vosk"}
        else settings.vad_pre_capture_gap_enter_ms
    )
    recorder = SoundDeviceRecorder(
        sample_rate=settings.capture_sample_rate,
        frame_size=settings.vad_frame_size,
        speech_threshold=settings.vad_speech_threshold,
        min_silence_ms=settings.vad_min_silence_ms,
        max_recording_ms=settings.vad_max_recording_ms,
        pre_roll_ms=settings.vad_pre_roll_ms,
        min_speech_ms=settings.vad_min_speech_ms,
        pre_capture_gap_ms=pre_capture_gap_ms,
    )
    if settings.stt_mode == "remote":
        transcriber = RemoteWhisperTranscriber(
            base_url=settings.remote_stt_url,
            language=settings.stt_language,
            timeout_seconds=settings.remote_stt_timeout_seconds,
        )
    else:
        transcriber = WhisperTranscriber(
            model_size=settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            language=settings.stt_language,
            beam_size=settings.whisper_beam_size,
        )
    transcriber.warm_up()
    return ListenUseCase(recorder=recorder, transcriber=transcriber)


def build_trigger(settings: Settings, *, input_fn: Callable[..., str] = input) -> Trigger:
    """Select the turn trigger (Strategy) from ``trigger_type``.

    ``input_fn`` is forwarded to the push-to-talk trigger (composition never
    touches stdin itself). The wake-word model is loaded lazily, only when the
    trigger starts listening.
    """
    if settings.trigger_type == "wake_word":
        return WakeWordTrigger(
            model_path=settings.wake_word_model_path,
            threshold=settings.wake_word_threshold,
            frame_size=settings.wake_word_frame_size,
            refractory_s=settings.wake_word_refractory_s,
            sample_rate=settings.capture_sample_rate,
        )
    if settings.trigger_type == "vosk":
        return VoskTrigger(
            model_path=settings.vosk_model_path,
            keyword=settings.vosk_keyword,
            frame_size=settings.vosk_frame_size,
            sample_rate=settings.capture_sample_rate,
        )
    return EnterTrigger(input_fn=input_fn)


def build_voice_loop(
    settings: Settings,
    *,
    should_continue: Callable[[], bool],
    input_fn: Callable[..., str] = input,
    on_state: Optional[Callable[[VoiceState], None]] = None,
    on_timing: Optional[Callable[[str, float], None]] = None,
) -> VoiceLoop:
    """Wire the full voice loop (Phases 3–5).

    Reuses the per-capability builders, so Whisper and Piper are each loaded once
    (warm) here, off the per-turn critical path. The trigger (push-to-talk or wake
    word) is selected from config; the loop and the turn share the same
    ``on_state`` callback (the turn emits LISTENING/THINKING/SPEAKING; the loop
    emits IDLE). The remaining I/O callables come from ``main``.
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
    trigger = build_trigger(settings, input_fn=input_fn)
    return VoiceLoop(
        turn,
        wait_for_trigger=trigger.wait_for_trigger,
        should_continue=should_continue,
        on_state=on_state,
    )
