"""Slice 3 Pipecat runtime/model identity recorder (FR-016, FR-035).

Builds the :class:`~opencloser.models.RealtimeProviderSession` recorded on every
Slice 3 session and surfaced in the run report (FR-036). The identity captures
``{runtime_name, runtime_version, provider_name, model_name, model_version}``
and — per FR-035 — MUST NOT carry credentials. The ``RealtimeProviderSession``
model is ``extra="forbid"``, so only the five named fields can ever be recorded;
:func:`build_runtime_identity` additionally rejects a provider whose ``identity``
dict exposes a credential-bearing key, failing loudly rather than silently
dropping it (defense in depth).
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

from opencloser.models import RealtimeProviderSession

if TYPE_CHECKING:
    from opencloser.runtime.base import RealtimeAIProvider

# The runtime name recorded for every Slice 3 session (Constitution: single
# telephony + single runtime). Matches ``RealtimeProviderSession`` default.
RUNTIME_NAME = "pipecat"
_PIPECAT_DISTRIBUTION = "pipecat-ai"

# Substrings that mark a dict key as credential-bearing (FR-035, case-insensitive).
_CREDENTIAL_KEY_MARKERS: tuple[str, ...] = (
    "key",
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "bearer",
)


def pipecat_runtime_version() -> str:
    """Return the installed ``pipecat-ai`` version, or ``"unknown"`` if absent."""
    try:
        return version(_PIPECAT_DISTRIBUTION)
    except PackageNotFoundError:  # pragma: no cover - environment-dependent
        return "unknown"


def _is_credential_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _CREDENTIAL_KEY_MARKERS)


def build_runtime_identity(
    provider: RealtimeAIProvider,
    *,
    runtime_version: str | None = None,
) -> RealtimeProviderSession:
    """Record the runtime + model identity for a session (FR-016).

    ``provider.identity`` supplies ``{provider_name, model_name, model_version}``
    (FR-016); the runtime name/version are stamped here. ``runtime_version``
    defaults to the installed ``pipecat-ai`` version.

    Raises:
        ValueError: if ``provider.identity`` exposes a credential-bearing key
            (FR-035) or is missing a required FR-016 field.
    """
    identity = dict(provider.identity)

    leaked = sorted(key for key in identity if _is_credential_key(key))
    if leaked:
        raise ValueError(
            f"provider identity exposed credential-bearing key(s) {leaked}; "
            "FR-035 forbids recording credentials"
        )

    try:
        return RealtimeProviderSession(
            runtime_name=RUNTIME_NAME,
            runtime_version=runtime_version or pipecat_runtime_version(),
            provider_name=identity["provider_name"],
            model_name=identity["model_name"],
            model_version=identity["model_version"],
        )
    except KeyError as exc:
        raise ValueError(f"provider identity missing required FR-016 field: {exc}") from exc
