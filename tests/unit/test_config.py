"""Unit tests for the TOML + env-var configuration loader (core/config.py — M5).

Covers TOML parsing, the `OPENCLOSER_*` env-var override layer, and the int-coercion
of `max_attempts` (env vars always arrive as strings).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from opencloser.core.config import load_config

pytestmark = pytest.mark.module("core")


_BASE_TOML = """\
[call_window]
start = "09:00"
end = "20:00"

[eligibility]
max_attempts = 5
default_timezone = "America/Los_Angeles"

[artifacts]
dir = "./artifacts"
schema_version = "slice1-v1"

[persona]
version = "alf-appointment-setter@0.1.0"

[state]
db = "./state/slice1.db"
"""


def _write_toml(tmp_path: Path, body: str = _BASE_TOML) -> Path:
    path = tmp_path / "slice1.toml"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clear_opencloser_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no stray OPENCLOSER_* vars from the real environment leak into a test."""
    for key in list(os.environ):
        if key.startswith("OPENCLOSER_"):
            monkeypatch.delenv(key, raising=False)


# -- TOML parsing ------------------------------------------------------------


def test_load_config_parses_toml(tmp_path: Path) -> None:
    config = load_config(_write_toml(tmp_path))
    assert config.call_window.start == "09:00"
    assert config.call_window.end == "20:00"
    assert config.eligibility.max_attempts == 5
    assert config.eligibility.default_timezone == "America/Los_Angeles"
    assert config.artifacts.dir == "./artifacts"
    assert config.artifacts.schema_version == "slice1-v1"
    assert config.persona.version == "alf-appointment-setter@0.1.0"
    assert config.state.db == "./state/slice1.db"


def test_load_config_rejects_malformed_toml(tmp_path: Path) -> None:
    """A TOML file missing a required section MUST fail validation."""
    partial = '[call_window]\nstart = "09:00"\nend = "20:00"\n'
    with pytest.raises(ValidationError):
        load_config(_write_toml(tmp_path, partial))


# -- env-var overrides -------------------------------------------------------


def test_env_var_overrides_take_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLOSER_CALL_WINDOW_START", "07:30")
    monkeypatch.setenv("OPENCLOSER_ELIGIBILITY_DEFAULT_TIMEZONE", "America/New_York")
    monkeypatch.setenv("OPENCLOSER_ARTIFACTS_DIR", "/var/opencloser/artifacts")
    monkeypatch.setenv("OPENCLOSER_PERSONA_VERSION", "alf-appointment-setter@9.9.9")
    monkeypatch.setenv("OPENCLOSER_STATE_DB", "/var/opencloser/state.db")

    config = load_config(_write_toml(tmp_path))

    assert config.call_window.start == "07:30"  # overridden
    assert config.call_window.end == "20:00"  # untouched TOML value
    assert config.eligibility.default_timezone == "America/New_York"
    assert config.artifacts.dir == "/var/opencloser/artifacts"
    assert config.persona.version == "alf-appointment-setter@9.9.9"
    assert config.state.db == "/var/opencloser/state.db"


def test_no_env_vars_leaves_toml_values_intact(tmp_path: Path) -> None:
    config = load_config(_write_toml(tmp_path))
    assert config.call_window.start == "09:00"
    assert config.eligibility.max_attempts == 5


# -- int coercion ------------------------------------------------------------


def test_max_attempts_env_override_is_int_coerced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`max_attempts` env vars arrive as strings; the loader MUST coerce to int."""
    monkeypatch.setenv("OPENCLOSER_ELIGIBILITY_MAX_ATTEMPTS", "9")
    config = load_config(_write_toml(tmp_path))
    assert config.eligibility.max_attempts == 9
    assert isinstance(config.eligibility.max_attempts, int)
