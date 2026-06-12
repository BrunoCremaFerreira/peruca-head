"""Generates the audio fixture used by the remote Whisper integration test.

Requires TTS to be enabled and PIPER_VOICE_PATH configured in the environment
or in a .env file at the project root.

Usage:
    python scripts/generate_stt_fixture.py
"""

import io
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Settings
from infra.tts.piper_speaker import PiperSpeaker

PHRASE = "olá peruca"
OUTPUT = Path(__file__).parent.parent / "src/tests/integration_tests/fixtures/ola_peruca.wav"


def main() -> None:
    settings = Settings()

    if not settings.tts_enabled or not settings.piper_voice_path:
        print(
            "ERROR: TTS_ENABLED=true and PIPER_VOICE_PATH must be set in .env "
            "to generate the fixture."
        )
        sys.exit(1)

    print(f"Synthesising '{PHRASE}' with {settings.piper_voice_path} ...")
    speaker = PiperSpeaker(
        model_path=settings.piper_voice_path,
        length_scale=settings.piper_length_scale,
    )
    audio = speaker.synthesize(PHRASE)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(audio.channels)
        wf.setsampwidth(audio.sample_width)
        wf.setframerate(audio.sample_rate)
        wf.writeframes(audio.pcm)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(buf.getvalue())
    print(f"Fixture written to {OUTPUT}  ({len(buf.getvalue())} bytes)")


if __name__ == "__main__":
    main()
