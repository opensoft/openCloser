"""Slice 3 real-time AI provider surface (research.md §3).

Defines the vendor-neutral pieces the Pipecat pipeline (T029) and runtime (T030)
consume so ``runtime/pipecat/`` stays provider-agnostic (Constitution §III):

- the frame types a provider streams back — :class:`TranscriptSegment`,
  :class:`ExtractionEvent`, :class:`AudioChunk`;
- :class:`ProviderSessionHandle`, the opaque per-session handle
  (``SessionHandle`` Protocol from ``runtime/base.py``);
- :func:`select_realtime_provider`, the deploy-time provider selection seam keyed
  by ``SLICE3_REALTIME_PROVIDER`` (research.md §3).

The concrete :class:`~opencloser.runtime.base.RealtimeAIProvider` Protocol lives
in ``runtime/base.py``. The first development/CI implementation is
``provider_fake.py``; real provider adapters are registered at deploy time.
Provider credentials come from env vars and MUST NEVER be logged or recorded
(FR-035).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opencloser.runtime.base import RealtimeAIProvider

# Env var selecting the deployment-configured provider (research.md §3). The
# default is the in-process fake so CI / rehearsal exercises the pipeline with
# zero real-provider tokens.
PROVIDER_ENV_VAR = "SLICE3_REALTIME_PROVIDER"
FAKE_PROVIDER_NAME = "fake-realtime"
# Sanctioned "no real-time provider configured" value (config/slice3.toml §"Required
# env vars"). A rehearsal-only deployment sets this; a real call is then unavailable
# and the US3 telephony-readiness gate must fail rather than the process crashing.
DISABLED_PROVIDER_NAME = "disabled"


class ProviderDisabledError(RuntimeError):
    """Raised by :func:`select_realtime_provider` when the real-time AI provider is
    configured as ``"disabled"`` (config/slice3.toml). Distinct from the
    unknown-provider ``ValueError`` so the US3 readiness check can map it to a
    "real-call unavailable (rehearsal only)" gate rather than a misconfiguration."""


@dataclass(frozen=True)
class TranscriptSegment:
    """A vendor-neutral transcript fragment streamed back from the provider."""

    text: str
    speaker: str = "caller"  # "caller" | "persona"


@dataclass(frozen=True)
class ExtractionEvent:
    """A vendor-neutral structured-extraction frame.

    The runtime MAY surface these to the persona module, but per FR-014 an
    ``ExtractionEvent`` MUST NOT set the final disposition — the deterministic
    Slice 1 rules own that.
    """

    field: str
    value: Any
    confidence: float = 1.0


@dataclass(frozen=True)
class AudioChunk:
    """A vendor-neutral outbound audio frame (μ-law 8 kHz per research.md §5)."""

    data: bytes


@dataclass(frozen=True)
class ProviderSessionHandle:
    """Opaque per-session handle (implements the ``SessionHandle`` Protocol)."""

    session_id: str


# A streamed frame is one of the vendor-neutral variants above.
ProviderFrame = TranscriptSegment | ExtractionEvent | AudioChunk


def select_realtime_provider(env: Mapping[str, str] | None = None) -> RealtimeAIProvider:
    """Select the deployment-configured real-time AI provider (research.md §3).

    Reads ``SLICE3_REALTIME_PROVIDER`` (default :data:`FAKE_PROVIDER_NAME`).
    Only the in-process fake is registered here; real provider adapters are
    wired at deploy time.

    Raises:
        ProviderDisabledError: the sanctioned ``"disabled"`` value — no
            real-time provider is configured (rehearsal-only deployment).
        ValueError: an unknown / typo'd provider name — a misconfigured
            deployment must fail loudly rather than silently falling back.
    """
    environ = os.environ if env is None else env
    name = environ.get(PROVIDER_ENV_VAR, FAKE_PROVIDER_NAME).strip() or FAKE_PROVIDER_NAME

    if name == DISABLED_PROVIDER_NAME:
        raise ProviderDisabledError(
            f"{PROVIDER_ENV_VAR}={DISABLED_PROVIDER_NAME!r}: no real-time AI provider is "
            "configured — real calls are unavailable (rehearsal-only deployment)"
        )

    if name == FAKE_PROVIDER_NAME:
        # Imported lazily to avoid a module-load cycle (provider_fake imports the
        # frame types defined above).
        from opencloser.runtime.pipecat.provider_fake import FakeRealtimeAIProvider

        return FakeRealtimeAIProvider()

    raise ValueError(
        f"unknown {PROVIDER_ENV_VAR}={name!r}; only {FAKE_PROVIDER_NAME!r} is registered "
        "in-tree — real provider adapters are wired at deploy time"
    )
