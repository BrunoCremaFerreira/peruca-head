"""Unit tests for trigger selection in the composition root.

build_trigger picks the adapter from settings.trigger_type without loading any
model (WakeWordTrigger lazy-loads openWakeWord only when it listens).
"""

from composition import build_trigger
from config import Settings
from infra.trigger.enter_trigger import EnterTrigger
from infra.trigger.vosk_trigger import VoskTrigger
from infra.trigger.wakeword_trigger import WakeWordTrigger


def test_builds_enter_trigger_by_default():
    trigger = build_trigger(Settings(_env_file=None), input_fn=lambda *_a: "")
    assert isinstance(trigger, EnterTrigger)


def test_builds_wake_word_trigger_when_configured():
    settings = Settings(
        _env_file=None, trigger_type="wake_word", wake_word_model_path="/m/peruca.onnx"
    )
    trigger = build_trigger(settings, input_fn=lambda *_a: "")
    assert isinstance(trigger, WakeWordTrigger)


def test_builds_vosk_trigger_when_configured():
    settings = Settings(
        _env_file=None,
        trigger_type="vosk",
        vosk_model_path="/models/vosk-model-small-pt-0.3",
    )
    trigger = build_trigger(settings, input_fn=lambda *_a: "")
    assert isinstance(trigger, VoskTrigger)
