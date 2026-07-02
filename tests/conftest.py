"""Shared pytest fixtures."""
from __future__ import annotations

import pytest


@pytest.fixture
def mock_mode():
    """Enable explicit offline mode (cfg.mock.enabled) for the duration of a test.

    The tools fail loud on a real run when the backend is unavailable, so tests
    that exercise the offline mock pipeline must opt in explicitly instead of
    relying on a silent fallback. get_settings() is a cached singleton, so the
    previous value is restored afterwards to avoid leaking into other tests.
    """
    from src.config import get_settings

    cfg = get_settings()
    prev = cfg.mock.enabled
    cfg.mock.enabled = True
    yield
    cfg.mock.enabled = prev
