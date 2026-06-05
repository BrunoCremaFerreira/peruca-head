"""Unit tests for SoundDeviceRecorder with sounddevice and the VAD injected.

No microphone and no torch/silero: frames are scripted and the VAD is a fake
that returns a scripted probability per chunk. The test pins the record-until-
silence state machine: speech detection, end-of-speech on sustained silence,
pre-roll inclusion, the safety timeout, and the 16k/mono/int16 output contract.

Frame timing is made tiny and exact: sample_rate=16000, frame_size=1600 -> each
frame is 100 ms, so the ms thresholds map to small whole numbers of frames.
"""

import numpy as np

from domain.models.audio_buffer import AudioBuffer
from infra.audio.sounddevice_recorder import SoundDeviceRecorder

FRAME_SIZE = 1600  # 100 ms at 16 kHz


def _frame(marker: int) -> np.ndarray:
    """A 100 ms int16 frame filled with a distinct marker value."""
    return np.full(FRAME_SIZE, marker, dtype=np.int16)


class _ScriptedVad:
    """Returns a scripted speech probability per call, ignoring the audio."""

    def __init__(self, probs):
        self._probs = list(probs)
        self.calls = 0

    def __call__(self, _chunk) -> float:
        prob = self._probs[self.calls] if self.calls < len(self._probs) else 0.0
        self.calls += 1
        return prob


def _recorder(frames, probs, **overrides):
    params = dict(
        vad=_ScriptedVad(probs),
        frame_source_factory=lambda: iter(frames),
        sleep=lambda _seconds: None,  # no real anti-leak gap delay in tests
        sample_rate=16000,
        channels=1,
        frame_size=FRAME_SIZE,
        speech_threshold=0.5,
        min_silence_ms=200,   # 2 frames
        max_recording_ms=2000,  # 20 frames
        pre_roll_ms=100,      # 1 frame
        min_speech_ms=100,    # 1 frame
    )
    params.update(overrides)
    return SoundDeviceRecorder(**params)


def test_waits_the_anti_leak_gap_before_capturing():
    # The cue's acoustic tail must die before capture opens: a fixed pre-capture
    # gap is slept before the first frame is read.
    slept: list = []
    frames = [_frame(1), _frame(2)]
    recorder = _recorder(
        frames, probs=[0.0, 0.0], sleep=lambda seconds: slept.append(seconds)
    )

    recorder.record_until_silence()

    assert slept and slept[0] >= 0.1  # >= 100 ms before any capture


def test_records_speech_and_stops_after_sustained_silence():
    frames = [_frame(1), _frame(2), _frame(3), _frame(4), _frame(5)]
    # silence, speech, speech, silence, silence -> stop after 2 silent frames
    recorder = _recorder(frames, probs=[0.0, 1.0, 1.0, 0.0, 0.0])

    buffer = recorder.record_until_silence()

    assert isinstance(buffer, AudioBuffer)
    assert buffer.sample_rate == 16000
    assert buffer.channels == 1
    assert buffer.sample_width == 2
    # pre-roll (frame 1) + speech (2,3) + trailing silence consumed before stop (4,5)
    expected = b"".join(_frame(i).tobytes() for i in (1, 2, 3, 4, 5))
    assert buffer.pcm == expected


def test_pre_roll_frame_before_speech_is_included():
    frames = [_frame(7), _frame(8), _frame(9), _frame(9)]
    recorder = _recorder(frames, probs=[0.0, 1.0, 0.0, 0.0])

    buffer = recorder.record_until_silence()

    # The leading silent frame (7) is prepended as pre-roll so the onset isn't clipped.
    assert buffer.pcm.startswith(_frame(7).tobytes())


def test_only_silence_returns_empty_buffer():
    frames = [_frame(1), _frame(2), _frame(3)]
    recorder = _recorder(frames, probs=[0.0, 0.0, 0.0])

    buffer = recorder.record_until_silence()

    assert buffer.is_empty()


def test_stops_at_max_recording_timeout():
    frames = [_frame(i) for i in range(1, 11)]
    recorder = _recorder(
        frames,
        probs=[1.0] * 10,           # continuous speech, never goes silent
        max_recording_ms=300,       # 3 frames
    )

    buffer = recorder.record_until_silence()

    assert not buffer.is_empty()
    assert buffer.frame_count == 3 * FRAME_SIZE
