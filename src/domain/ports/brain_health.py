"""BrainHealthCheck port: a startup liveness probe for the brain.

Kept separate from :class:`~domain.ports.brain_client.BrainClient` (Interface
Segregation): ``ask`` runs every turn on the critical path, while ``check_health``
runs once at startup. Returning a ``bool`` (not raising) matches the
warn-and-continue policy: the caller wants an ok/not-ok to log, not an error.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BrainHealthCheck(ABC):
    """Probes whether the brain is reachable and healthy."""

    @abstractmethod
    def check_health(self) -> bool:
        """Return True if the brain reports healthy; False on any error/timeout."""
        raise NotImplementedError
