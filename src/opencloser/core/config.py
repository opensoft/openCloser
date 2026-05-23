"""TOML + env-var configuration loader (research.md §Configuration surface).

`config/slice1.toml` provides defaults. Each top-level key may be overridden by an
environment variable of the form ``OPENCLOSER_<SECTION>_<KEY>``.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from opencloser.models import DataverseSecrets, Slice2Config, SliceConfig

ENV_PREFIX = "OPENCLOSER_"

# Map env-var-name-fragments to (section, key) in the TOML structure.
_ENV_MAP: dict[str, tuple[str, str]] = {
    "CALL_WINDOW_START": ("call_window", "start"),
    "CALL_WINDOW_END": ("call_window", "end"),
    "ELIGIBILITY_MAX_ATTEMPTS": ("eligibility", "max_attempts"),
    "ELIGIBILITY_DEFAULT_TIMEZONE": ("eligibility", "default_timezone"),
    "ARTIFACTS_DIR": ("artifacts", "dir"),
    "ARTIFACTS_SCHEMA_VERSION": ("artifacts", "schema_version"),
    "PERSONA_VERSION": ("persona", "version"),
    "STATE_DB": ("state", "db"),
}


def load_config(toml_path: str | Path) -> SliceConfig:
    """Load + validate Slice 1 config from TOML, then apply env-var overrides."""
    raw = _read_toml(Path(toml_path))
    _apply_env_overrides(raw)
    return SliceConfig.model_validate(raw)


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _apply_env_overrides(raw: dict[str, Any]) -> None:
    for env_suffix, (section, key) in _ENV_MAP.items():
        value = os.environ.get(ENV_PREFIX + env_suffix)
        if value is None:
            continue
        section_dict = raw.setdefault(section, {})
        # Coerce int-valued keys.
        if key == "max_attempts":
            section_dict[key] = int(value)
        else:
            section_dict[key] = value


# ---------------------------------------------------------------------------
# Slice 2 — non-secret config (config/slice2.toml) + Dataverse secrets (env)
# ---------------------------------------------------------------------------

# Dataverse connection secret env var -> DataverseSecrets field (spec FR-005).
_DATAVERSE_SECRET_ENV: dict[str, str] = {
    "DATAVERSE_TENANT_ID": "tenant_id",
    "DATAVERSE_CLIENT_ID": "client_id",
    "DATAVERSE_CLIENT_SECRET": "client_secret",
    "DATAVERSE_ENV_URL": "env_url",
}

# OPENCLOSER_<SECTION>_<KEY> -> (toml section, key) — Slice 2 non-secret overrides.
# Same loader pattern as Slice 1's _ENV_MAP (research.md §5). List-valued keys
# (backoff_seconds, patterns) are not env-overridable.
_SLICE2_ENV_MAP: dict[str, tuple[str, str]] = {
    "RUN_DEFAULT_MODE": ("run", "default_mode"),
    "RUN_CAMPAIGN": ("run", "campaign"),
    "DATAVERSE_MAPPING_ARTIFACT": ("dataverse", "mapping_artifact"),
    "DATAVERSE_CALLABLE_STATUS": ("dataverse", "callable_status"),
    "RETRY_MAX_RETRIES": ("retry", "max_retries"),
    "RETRY_RETRY_AFTER_CAP_SECONDS": ("retry", "retry_after_cap_seconds"),
    "TASK_OWNERS_CALLBACK": ("task_owners", "callback"),
    "TASK_OWNERS_REVIEW": ("task_owners", "review"),
    "REDACTION_POLICY": ("redaction", "policy"),
    "REDACTION_RETENTION": ("redaction", "retention"),
}


class Slice2ConfigError(RuntimeError):
    """Raised when Slice 2 config or Dataverse secrets are missing or invalid (FR-007)."""


def _apply_slice2_env_overrides(raw: dict[str, Any]) -> None:
    """Apply ``OPENCLOSER_<SECTION>_<KEY>`` overrides to a parsed slice2.toml dict."""
    for env_suffix, (section, key) in _SLICE2_ENV_MAP.items():
        value = os.environ.get(ENV_PREFIX + env_suffix)
        if value is None:
            continue
        section_dict = raw.setdefault(section, {})
        # Coerce typed keys; string keys pass through untouched.
        if key == "max_retries":
            section_dict[key] = int(value)
        elif key == "retry_after_cap_seconds":
            section_dict[key] = float(value)
        else:
            section_dict[key] = value


def load_slice2_config(toml_path: str | Path) -> Slice2Config:
    """Load + validate the non-secret Slice 2 configuration from config/slice2.toml (FR-006).

    Each scalar key may be overridden by an environment variable of the form
    ``OPENCLOSER_<SECTION>_<KEY>`` (matching the Slice 1 loader pattern —
    research.md §5).
    """
    raw = _read_toml(Path(toml_path))
    _apply_slice2_env_overrides(raw)
    return Slice2Config.model_validate(raw)


def missing_dataverse_secret_env_vars() -> list[str]:
    """Return the names of any required Dataverse secret env vars that are unset or empty."""
    return [name for name in _DATAVERSE_SECRET_ENV if not os.environ.get(name)]


def load_dataverse_secrets() -> DataverseSecrets:
    """Load Dataverse connection secrets from environment variables (FR-005).

    Raises ``Slice2ConfigError`` naming every missing variable (FR-007). Callers that
    run in dry-run mode should gate this behind a run-mode check — dry-run does not
    require write credentials.
    """
    missing = missing_dataverse_secret_env_vars()
    if missing:
        raise Slice2ConfigError(
            "missing required Dataverse secret environment variable(s): " + ", ".join(missing)
        )
    return DataverseSecrets(
        **{field: os.environ[name] for name, field in _DATAVERSE_SECRET_ENV.items()}
    )
