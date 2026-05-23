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

# Built-in redaction patterns applied by ``RegexRedactionPolicy`` in addition to any
# user-supplied patterns from ``[redaction] patterns``. Covers common direct-identifier
# leakage in scripted demo transcripts (phone numbers, emails).
_BUILTIN_PATTERNS: tuple[str, ...] = (
    # Email addresses.
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    # North American phone numbers — at least one separator required between segments
    # so bare 10-digit IDs are not redacted. Matches: 555-123-4567, (555) 123-4567,
    # 555.123.4567, +1 555 123 4567.
    r"(?:\+?\d{1,2}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}",
)


class Policy(Protocol):
    def redact(self, transcript_text: str) -> str: ...


@dataclass(frozen=True, slots=True)
class NoOpPolicy:
    """Returns transcript text unchanged (FR-029)."""

    def redact(self, transcript_text: str) -> str:
        return transcript_text


@dataclass(frozen=True, slots=True)
class RegexRedactionPolicy:
    """Replaces every match of the compiled patterns with ``[REDACTED]`` (FR-028)."""

    _compiled: tuple[re.Pattern[str], ...]
    replacement: str = DEFAULT_REPLACEMENT

    @classmethod
    def from_patterns(
        cls,
        extra_patterns: list[str] | tuple[str, ...] = (),
        *,
        replacement: str = DEFAULT_REPLACEMENT,
    ) -> RegexRedactionPolicy:
        compiled: list[re.Pattern[str]] = []
        for raw in (*_BUILTIN_PATTERNS, *extra_patterns):
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
        """Default-on layer: regex policy + full retention (FR-028 default)."""
        return cls(
            policy=RegexRedactionPolicy.from_patterns(),
            _retention_mode="full",
        )
