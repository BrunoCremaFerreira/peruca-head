"""In-memory fake of the BrainHealthCheck port."""

from __future__ import annotations

from dataclasses import dataclass

from domain.ports.brain_health import BrainHealthCheck


@dataclass
class FakeBrainHealthCheck(BrainHealthCheck):
    """A scriptable health check: returns ``healthy`` or raises if ``raises``."""

    healthy: bool = True
    raises: bool = False
    calls: int = 0

    def check_health(self) -> bool:
        self.calls += 1
        if self.raises:
            raise RuntimeError("health probe blew up")
        return self.healthy
