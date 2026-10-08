"""Playwright E2E fixtures.

Drives a real browser (pytest-playwright) against the real app running in pytest-django's
live_server. Tests are order-independent: transactional_db truncates tables between tests, and the
landing story processes its bundled samples on first request.

Run:  pytest e2e/              (headless)
      pytest e2e/ --headed     (watch it locally)
"""
import pytest

from core.testing import SAMPLES


@pytest.fixture
def site(live_server, transactional_db):
    return live_server.url


@pytest.fixture
def sample():
    return lambda name: str(SAMPLES / name)
