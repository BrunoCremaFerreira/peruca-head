"""TurnOutcome: the result of one voice turn, for the loop and for tests.

A minimal discriminator (no payload — YAGNI). It lets the loop and the test
suite assert what happened in a turn without inspecting I/O.
"""

from __future__ import annotations

from enum import Enum, auto


class TurnOutcome(Enum):
    """How a single voice turn ended."""

    SUCCESS = auto()      # transcribed, asked the brain, spoke the reply
    EMPTY = auto()        # no speech detected — short-circuited before the brain
    BRAIN_ERROR = auto()  # brain unreachable — spoke a pt-BR error instead
