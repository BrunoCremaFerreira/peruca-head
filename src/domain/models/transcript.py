"""Transcript: text recognised from speech (the STT result).

A pure value object, mirroring :class:`~domain.models.reply.Reply`. It carries
no behaviour beyond representing recognised text and whether it is empty.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Transcript:
    """An immutable value object wrapping recognised speech text."""

    text: str

    def is_empty(self) -> bool:
        """True when the transcript has no meaningful (non-whitespace) content."""
        return self.text.strip() == ""
