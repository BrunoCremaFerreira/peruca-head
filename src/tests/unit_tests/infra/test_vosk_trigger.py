"""Unit tests for VoskTrigger.

All tests are deterministic: no mic, no Vosk model, no disk access.
The recognizer (Callable[[np.ndarray], bool]) and frame source are injected.
"""

import numpy as np
import pytest

from infra.trigger.vosk_trigger import VoskTrigger


class _ClosableFrames:
    """Frame iterator that records when it was closed (mirrors test_wakeword_trigger)."""

    def __init__(self, frames):
        self._it = iter(frames)
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._it)

    def close(self):
        self.closed = True


class _ScriptedRecognizer:
    """Returns scripted bools, one per call."""

    def __init__(self, results: list[bool]):
        self._results = list(results)
        self.calls = 0

    def __call__(self, _frame: np.ndarray) -> bool:
        result = self._results[self.calls] if self.calls < len(self._results) else False
        self.calls += 1
        return result


def _trigger(frames: list, results: list[bool], **overrides):
    source = _ClosableFrames(frames)
    params = dict(
        recognizer=_ScriptedRecognizer(results),
        frame_source_factory=lambda: source,
        frame_size=4000,
    )
    params.update(overrides)
    trigger = VoskTrigger(
        model_path="ignored-model-dir",
        keyword="peruca",
        **params,
    )
    return trigger, source


_DUMMY_FRAME = np.zeros(4000, dtype=np.int16)
_FRAMES = [_DUMMY_FRAME] * 5


def test_returns_when_recognizer_returns_true():
    trigger, _ = _trigger(_FRAMES, [False, False, True, False, False])
    trigger.wait_for_trigger()  # must return, not raise


def test_closes_stream_before_returning():
    trigger, source = _trigger(_FRAMES, [False, False, True])
    trigger.wait_for_trigger()
    assert source.closed is True


def test_closes_stream_even_when_frames_exhausted():
    # for-loop exhaustion is caught by Python; wait_for_trigger returns None.
    trigger, source = _trigger(_FRAMES, [False] * 5)
    trigger.wait_for_trigger()
    assert source.closed is True


def test_does_not_fire_when_recognizer_always_false():
    # Returns without detecting; recognizer is called for all frames.
    rec = _ScriptedRecognizer([False] * 5)
    source = _ClosableFrames([_DUMMY_FRAME] * 5)
    trigger = VoskTrigger(
        model_path="ignored",
        keyword="peruca",
        recognizer=rec,
        frame_source_factory=lambda: source,
    )
    trigger.wait_for_trigger()
    assert rec.calls == 5


def test_recognizer_called_for_each_frame():
    rec = _ScriptedRecognizer([False, False, True])
    source = _ClosableFrames([_DUMMY_FRAME] * 3)
    trigger = VoskTrigger(
        model_path="ignored",
        keyword="peruca",
        recognizer=rec,
        frame_source_factory=lambda: source,
    )
    trigger.wait_for_trigger()
    assert rec.calls == 3  # called on every frame until detection
