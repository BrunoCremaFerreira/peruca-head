"""Unit tests for SoundDevicePlayer with the sounddevice backend injected.

`sounddevice` is never imported (it needs system PortAudio); a mock backend is
injected. The test pins that PCM bytes reach the backend as an int16 array at
the buffer's own sample rate, and that empty buffers play nothing.
"""

from unittest.mock import Mock

import numpy as np

from domain.models.audio_buffer import AudioBuffer
from infra.audio.sounddevice_player import SoundDevicePlayer


def test_plays_pcm_as_int16_array_at_buffer_sample_rate():
    backend = Mock()
    player = SoundDevicePlayer(backend=backend)
    buffer = AudioBuffer(
        pcm=b"\x01\x00\x02\x00", sample_rate=22050, channels=1, sample_width=2
    )

    player.play(buffer)

    backend.play.assert_called_once()
    args, kwargs = backend.play.call_args
    array = args[0]
    assert array.dtype == np.dtype("int16")
    assert list(array) == [1, 2]
    assert kwargs["samplerate"] == 22050
    backend.wait.assert_called_once()


def test_empty_buffer_plays_nothing():
    backend = Mock()
    player = SoundDevicePlayer(backend=backend)

    player.play(AudioBuffer.empty())

    backend.play.assert_not_called()
    backend.wait.assert_not_called()
