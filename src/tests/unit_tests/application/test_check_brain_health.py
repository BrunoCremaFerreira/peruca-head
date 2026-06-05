"""Unit tests for CheckBrainHealthUseCase (warn-and-continue semantics)."""

from application.use_cases.check_brain_health import CheckBrainHealthUseCase
from tests.fakes.fake_brain_health_check import FakeBrainHealthCheck


def test_returns_true_when_brain_is_healthy():
    use_case = CheckBrainHealthUseCase(FakeBrainHealthCheck(healthy=True))
    assert use_case.run() is True


def test_returns_false_when_brain_is_unhealthy():
    use_case = CheckBrainHealthUseCase(FakeBrainHealthCheck(healthy=False))
    assert use_case.run() is False


def test_never_raises_even_if_the_probe_throws():
    # warn-and-continue: a failing probe must not crash startup.
    use_case = CheckBrainHealthUseCase(FakeBrainHealthCheck(raises=True))
    assert use_case.run() is False
