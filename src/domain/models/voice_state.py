"""VoiceState: the states of the push-to-talk loop, for console/LED feedback.

A pure enum with no behaviour. The VoiceTurn emits LISTENING/THINKING/SPEAKING
during a turn; the VoiceLoop owns IDLE between turns.
"""

from __future__ import annotations

from enum import Enum, auto


class VoiceState(Enum):
    """Where the voice loop currently is."""

    IDLE = auto()       # waiting for the trigger (Enter)
    LISTENING = auto()  # capturing speech (VAD)
    THINKING = auto()   # transcribing + asking the brain
    SPEAKING = auto()   # synthesizing + playing the reply
