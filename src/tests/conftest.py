"""Shared pytest configuration for the head's test suite.

Integration tests (marked ``integration``) are opt-in: they are skipped unless
``-m integration`` is requested, so the default run never needs a live peruca.
"""

import pytest


def pytest_collection_modifyitems(config, items):
    if config.getoption("-m"):
        return
    skip_integration = pytest.mark.skip(reason="needs -m integration (live peruca)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
