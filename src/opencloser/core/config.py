"""TOML + env-var configuration loader (research.md §Configuration surface).

`config/slice1.toml` provides defaults. Each top-level key may be overridden by an
environment variable of the form ``OPENCLOSER_<SECTION>_<KEY>``.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from opencloser.models import SliceConfig

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
