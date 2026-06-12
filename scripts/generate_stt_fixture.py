"""Generates the audio fixture used by the remote Whisper integration test.

Modes tried in order:
  1. Piper TTS  — silent, automated. Requires TTS_ENABLED=true and PIPER_VOICE_PATH in .env.
  2. arecord    — interactive fallback using ALSA (Linux). Prompts you to say the phrase.
  3. sounddevice— interactive fallback using PortAudio (cross-platform, needs libportaudio2).

Usage:
    python scripts/generate_stt_fixture.py
"""

import io
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

PHRASE = "olá peruca"
SAMPLE_RATE = 16000
RECORD_SECONDS = 4
OUTPUT = Path(__file__).parent.parent / "src/tests/integration_tests/fixtures/ola_peruca.wav"


def _save_wav(pcm: bytes, sample_rate: int, channels: int, sample_width: int) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    OUTPUT.write_bytes(buf.getvalue())
    print(f"Fixture written to {OUTPUT}  ({len(buf.getvalue())} bytes)")


def _try_piper() -> bool:
    try:
        from config import Settings
        from infra.tts.piper_speaker import PiperSpeaker
    except ImportError:
        return False

    settings = Settings()
    if not settings.tts_enabled or not settings.piper_voice_path:
        return False

    print(f"Synthesising '{PHRASE}' with {settings.piper_voice_path} ...")
    speaker = PiperSpeaker(
        model_path=settings.piper_voice_path,
        length_scale=settings.piper_length_scale,
    )
    audio = speaker.synthesize(PHRASE)
    _save_wav(audio.pcm, audio.sample_rate, audio.channels, audio.sample_width)
    return True


def _try_arecord() -> bool:
    """Records via ALSA arecord (Linux). Returns True if successful."""
    result = subprocess.run(["which", "arecord"], capture_output=True)
    if result.returncode != 0:
        return False

    print(f"\nMicrophone mode (arecord) — no TTS configured.")
    print(f'When ready, say clearly: "{PHRASE}"')
    input("Press Enter to start recording...")

    print(f"Recording {RECORD_SECONDS}s — speak now!")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "arecord",
            "--format=S16_LE",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
            f"--duration={RECORD_SECONDS}",
            str(OUTPUT),
        ],
        check=True,
    )
    print(f"Done. Fixture written to {OUTPUT}")
    return True


def _try_sounddevice() -> bool:
    """Records via sounddevice + PortAudio. Returns True if successful."""
    try:
        import numpy as np
        import sounddevice as sd
    except (ImportError, OSError):
        return False

    print(f"\nMicrophone mode (sounddevice) — no TTS configured.")
    print(f'When ready, say clearly: "{PHRASE}"')
    input("Press Enter to start recording...")

    print(f"Recording {RECORD_SECONDS}s — speak now!")
    recording = sd.rec(
        int(SAMPLE_RATE * RECORD_SECONDS),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    print("Done.")
    _save_wav(recording.tobytes(), SAMPLE_RATE, 1, 2)
    return True


def main() -> None:
    if _try_piper():
        return
    if _try_arecord():
        return
    if _try_sounddevice():
        return
    print(
        "ERROR: No TTS or recording method available.\n"
        "Options:\n"
        "  - Set TTS_ENABLED=true and PIPER_VOICE_PATH in .env\n"
        "  - Install arecord (apt install alsa-utils)\n"
        "  - Install libportaudio2 + pip install sounddevice"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
