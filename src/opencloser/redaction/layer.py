"""Transcript redaction layer (FR-028, FR-029, FR-030).

See ``specs/002-mock-call-real-crm/contracts/redaction-layer.md``. The layer is
default-on; disabling redaction requires an explicit ``policy = "noop"`` in
``config/slice2.toml [redaction]``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

from opencloser.models import RedactionPolicyConfig

RetentionMode = Literal["full", "summary-only"]

DEFAULT_REPLACEMENT = "[REDACTED]"


class Policy(Protocol):
    def redact(self, transcript_text: str) -> str: ...


@dataclass(frozen=True, slots=True)
class NoOpPolicy:
    """Returns transcript text byte-identical at the layer level (FR-029).

    Note: ``artifacts/writer._write_text_atomic`` may append a trailing LF to
    the text when the input lacks one (writer-level normalization). The
    no-op policy itself does not modify bytes; the on-disk transcript may
    therefore differ by at most one trailing newline. The Slice 1 unredacted
    contract was always written through the same writer, so this matches
    pre-Slice-2 behavior.
    """

    def redact(self, transcript_text: str) -> str:
        return transcript_text


@dataclass(frozen=True, slots=True)
class RegexRedactionPolicy:
    """Replaces every match of the compiled patterns with ``[REDACTED]`` (FR-028).

    Compiles exactly the patterns it is given — no implicit built-ins. The
    config-driven default set lives in
    ``opencloser.models.BUILTIN_REDACTION_PATTERNS`` and is wired in via
    ``RedactionPolicyConfig.patterns`` so config and code cannot drift.
    """

    _compiled: tuple[re.Pattern[str], ...]
    replacement: str = DEFAULT_REPLACEMENT

    @classmethod
    def from_patterns(
        cls,
        patterns: list[str] | tuple[str, ...] = (),
        *,
        replacement: str = DEFAULT_REPLACEMENT,
    ) -> RegexRedactionPolicy:
        compiled: list[re.Pattern[str]] = []
        for raw in patterns:
            try:
                compiled.append(re.compile(raw))
            except re.error as exc:
                raise ValueError(f"Invalid redaction regex {raw!r}: {exc}") from exc
        return cls(_compiled=tuple(compiled), replacement=replacement)

    def redact(self, transcript_text: str) -> str:
        out = transcript_text
        for pattern in self._compiled:
            out = pattern.sub(self.replacement, out)
        return out


@dataclass(frozen=True, slots=True)
class RedactionLayer:
    """Transforms transcript text and decides whether a transcript file is written."""

    policy: Policy
    _retention_mode: RetentionMode

    def redact(self, transcript_text: str) -> str:
        return self.policy.redact(transcript_text)

    def retention_mode(self) -> RetentionMode:
        return self._retention_mode

    @classmethod
    def from_config(cls, config: RedactionPolicyConfig) -> RedactionLayer:
        """Build a layer from validated ``[redaction]`` config (FR-028..FR-030).

        Raises ``ValueError`` if any user pattern is not a valid regex — the
        orchestrator surfaces this as a readiness failure.
        """
        policy: Policy
        if config.policy == "regex":
            policy = RegexRedactionPolicy.from_patterns(config.patterns)
        elif config.policy == "noop":
            policy = NoOpPolicy()
        else:  # pragma: no cover - pydantic Literal guards this
            raise ValueError(f"Unknown redaction policy: {config.policy!r}")
        return cls(policy=policy, _retention_mode=config.retention)

    @classmethod
    def default(cls) -> RedactionLayer:
        """Default-on layer (FR-028): mirrors the unconfigured ``[redaction]`` section
        so the implicit default and the config-driven default cannot drift apart.

        Used by Slice 2 readiness via ``from_config(slice2_config.redaction)`` when
        the operator hasn't overridden ``[redaction]`` in slice2.toml. NOT used as
        the writer's silent fallback for callers that don't pass a layer — that
        path uses :meth:`noop` so a Slice 1 caller doesn't get redaction it
        didn't ask for (Copilot PR #3 LOW)."""
        return cls.from_config(RedactionPolicyConfig())

    @classmethod
    def noop(cls) -> RedactionLayer:
        """No-op layer: leaves transcript bytes unchanged, retention=full.

        This is the writer's silent fallback when a caller omits
        ``redaction_layer`` — restores the pre-Slice-2 behavior where transcripts
        were written verbatim (Slice 1 spec deferred redaction to Slice 2).
        Slice 2 callers MUST pass the configured layer explicitly (the runner's
        readiness gate builds it via :meth:`from_config`), so this fallback only
        affects callers that predate the Slice 2 redaction contract."""
        return cls(policy=NoOpPolicy(), _retention_mode="full")
