"""T119 — Slice 3 non-secret config loader (`config/slice3.toml`).

Parses the six `config/slice3.toml` sections (research §11) into the runtime
objects ``run_slice3`` needs — primarily the :class:`Slice3TelephonyConfig` the
readiness checker validates, plus the shadow-STT default. Secrets are never read
from TOML (FR-035); SignalWire credential *presence* is derived from the
environment so the readiness check can report whether they are configured
without ever recording their values.

Configuration precedence is CLI flag > env var > ``config/slice3.toml`` >
built-in default (R4-Q7 / research §11); this loader supplies the TOML + default
layers, and ``run_slice3`` applies any CLI / env override on top.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from opencloser.slice3.readiness import Slice3TelephonyConfig

_DEFAULT_CONFIG_PATH = "config/slice3.toml"

# SignalWire credential env vars (quickstart §1.2). Presence — never values — is
# what the readiness check reports.
_SIGNALWIRE_CREDENTIAL_ENV = (
    "SIGNALWIRE_PROJECT_ID",
    "SIGNALWIRE_API_TOKEN",
    "SIGNALWIRE_SIGNING_SECRET",
)


@dataclass(frozen=True, slots=True)
class Slice3Config:
    """The loaded non-secret Slice 3 configuration."""

    telephony: Slice3TelephonyConfig
    shadow_stt_enabled_default: bool = False
    config_path: Path | None = None
    config_found: bool = False


def _signalwire_credentials_present() -> bool:
    return all(os.environ.get(name) for name in _SIGNALWIRE_CREDENTIAL_ENV)


def load_slice3_config(config_path: str | Path | None) -> Slice3Config:
    """Load ``config/slice3.toml`` into a :class:`Slice3Config`.

    A missing file yields an all-empty telephony config (every readiness check
    that depends on it will fail), which is the correct rehearsal behavior:
    surface the gap, never silently pass. Mapping-derived checks
    (``campaign_persona_runtime_mapping``, ``task_owner_mapping``) default to
    ``False`` here because they require a loaded Dataverse mapping the
    config-only path does not have; ``run_slice3``'s real-call path supplies the
    real values when a Dataverse client is available.
    """
    path = Path(config_path) if config_path else Path(_DEFAULT_CONFIG_PATH)
    found = path.is_file()
    data: dict = {}
    if found:
        with path.open("rb") as fh:
            data = tomllib.load(fh)

    signalwire = data.get("signalwire", {}) if isinstance(data, dict) else {}
    shadow = data.get("shadow_stt", {}) if isinstance(data, dict) else {}

    telephony = Slice3TelephonyConfig(
        signalwire_credentials_present=_signalwire_credentials_present(),
        source_caller_id=signalwire.get("source_caller_id"),
        status_callback_url_template=signalwire.get("status_callback_url_template"),
        media_callback_url_template=signalwire.get("media_callback_url_template"),
        # Mapping-derived; unknown without a loaded Dataverse mapping.
        campaign_persona_runtime_mapping_present=False,
        task_owner_mapping_present=False,
    )
    return Slice3Config(
        telephony=telephony,
        shadow_stt_enabled_default=bool(shadow.get("enabled_default", False)),
        config_path=path,
        config_found=found,
    )


__all__ = ("Slice3Config", "load_slice3_config")
