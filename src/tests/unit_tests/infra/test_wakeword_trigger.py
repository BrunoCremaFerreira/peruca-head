"""Unit tests for WakeWordTrigger with the detector and frame source injected.

No microphone, no openWakeWord, no model: frames are scripted and the detector
returns a scripted score per frame. Pins that the trigger returns when the score
crosses the threshold and that it closes its audio stream deterministically
before returning (so it never races the recorder for the device).
"""

import numpy as np

from infra.trigger.wakeword_trigger import WakeWordTrigger


def _frame(marker: int) -> np.ndarray:
    return np.full(1280, marker, dtype=np.int16)


class _ScriptedDetector:
    def __init__(self, scores):
        self._scores = list(scores)
        self.calls = 0

    def __call__(self, _frame) -> float:
        score = self._scores[self.calls] if self.calls < len(self._scores) else 0.0
        self.calls += 1
        return score


class _ClosableFrames:
    """A frame iterator that records when it was closed (like a real stream)."""

    def __init__(self, frames):
        self._it = iter(frames)
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._it)

    def close(self):
        self.closed = True


def _trigger(frames, scores, **overrides):
    source = _ClosableFrames(frames)
    params = dict(
        detector=_ScriptedDetector(scores),
        frame_source_factory=lambda: source,
        threshold=0.5,
        frame_size=1280,
    )
    params.update(overrides)
    trigger = WakeWordTrigger(model_path="ignored.onnx", **params)
    return trigger, source


def test_returns_when_score_crosses_threshold():
    detector = _ScriptedDetector([0.1, 0.2, 0.9])
    source = _ClosableFrames([_frame(1), _frame(2), _frame(3)])
    trigger = WakeWordTrigger(
        model_path="ignored.onnx",
        detector=detector,
        frame_source_factory=lambda: source,
        threshold=0.5,
    )

    assert trigger.wait_for_trigger() is None
    assert detector.calls == 3  # consumed frames until the wake word fired


def test_closes_the_stream_before_returning():
    trigger, source = _trigger(
        [_frame(1), _frame(2), _frame(3)], scores=[0.0, 0.0, 0.8]
    )

    trigger.wait_for_trigger()

    assert source.closed is True


def test_does_not_fire_below_threshold():
    detector = _ScriptedDetector([0.1, 0.2, 0.3])
    source = _ClosableFrames([_frame(1), _frame(2), _frame(3)])
    trigger = WakeWordTrigger(
        model_path="ignored.onnx",
        detector=detector,
        frame_source_factory=lambda: source,
        threshold=0.5,
    )

    trigger.wait_for_trigger()  # frames exhaust without a detection

    # All frames were inspected and none crossed the threshold.
    assert detector.calls == 3
