"""Trigger port: the Strategy that decides when a turn starts.

A push-to-talk key, a wake word, or anything else — the loop only needs "block
until the user wants to talk". The return value carries nothing; the trigger
having returned is the whole signal.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Trigger(ABC):
    """Blocks until the user signals the start of a turn."""

    @abstractmethod
    def wait_for_trigger(self) -> None:
        """Return once a turn should begin."""
        raise NotImplementedError
