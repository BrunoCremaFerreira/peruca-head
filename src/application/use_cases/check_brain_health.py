"""CheckBrainHealthUseCase: probe the brain at startup, warn-and-continue.

A thin wrapper over the :class:`BrainHealthCheck` port whose only job is to make
the warn-and-continue policy explicit and testable: it returns a bool and never
raises, so a failed (or throwing) probe can never crash startup.
"""

from __future__ import annotations

from domain.ports.brain_health import BrainHealthCheck


class CheckBrainHealthUseCase:
    """Returns whether the brain looks healthy; never raises."""

    def __init__(self, health_check: BrainHealthCheck) -> None:
        self._health_check = health_check

    def run(self) -> bool:
        try:
            return self._health_check.check_health()
        except Exception:
            return False
