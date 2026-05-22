"""Shared pytest fixtures (research.md §Tests)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.state import store


@pytest.fixture
def frozen_clock() -> FrozenClock:
    """A FrozenClock fixed at 2026-05-19T17:00:00Z for deterministic tests."""
    return FrozenClock(datetime(2026, 5, 19, 17, 0, 0, tzinfo=UTC))


@pytest.fixture
def tmp_state_db(tmp_path: Path, frozen_clock: FrozenClock) -> Iterator[sqlite3.Connection]:
    """A fresh SQLite database with schema applied; isolated to one test."""
    db_path = tmp_path / "slice1.db"
    conn = store.connect(db_path)
    try:
        store.init_schema(conn, now_utc_ms=frozen_clock.now_utc_ms())
        yield conn
    finally:
        conn.close()


@pytest.fixture
def tmp_artifact_dir(tmp_path: Path) -> Path:
    """A scratch artifact directory per test."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    return artifacts
