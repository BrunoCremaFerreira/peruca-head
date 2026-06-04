"""Reply: the textual answer the brain (peruca) returns for a message.

A pure value object. It carries no behaviour beyond representing recognised
reply text and answering whether it is empty.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reply:
    """An immutable value object wrapping the brain's reply text."""

    text: str

    def is_empty(self) -> bool:
        """True when the reply has no meaningful (non-whitespace) content."""
        return self.text.strip() == ""
