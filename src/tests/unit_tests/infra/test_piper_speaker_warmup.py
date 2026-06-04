"""Unit tests for PiperSpeaker eager warm-up (load the voice once, up front).

The composition root warms the voice at startup so the first real utterance is
not slowed by model loading and a missing voice fails at boot, not mid-talk.
A fake loader stands in for ``piper`` so no model is touched.
"""

from infra.tts.piper_speaker import PiperSpeaker


class _FakeChunk:
    audio_int16_bytes = b"\x01\x00"
    sample_rate = 22050
    sample_channels = 1
    sample_width = 2


class _FakeVoice:
    def synthesize(self, text, syn_config=None):
        return iter([_FakeChunk()])


def test_warm_up_loads_the_voice_exactly_once():
    loads: list[str] = []

    def loader(path):
        loads.append(path)
        return _FakeVoice()

    speaker = PiperSpeaker(model_path="voice.onnx", voice_loader=loader)

    speaker.warm_up()
    speaker.warm_up()  # idempotent
    speaker.synthesize("oi")  # reuses the warm voice, no reload

    assert loads == ["voice.onnx"]


def test_lazy_load_still_happens_on_first_synthesize_without_warm_up():
    loads: list[str] = []

    def loader(path):
        loads.append(path)
        return _FakeVoice()

    speaker = PiperSpeaker(model_path="voice.onnx", voice_loader=loader)

    speaker.synthesize("oi")

    assert loads == ["voice.onnx"]
