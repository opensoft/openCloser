"""Transcript redaction layer (FR-028, FR-029, FR-030 — Slice 2).

See ``specs/002-mock-call-real-crm/contracts/redaction-layer.md``. The layer is
default-on; disabling redaction requires an explicit ``policy = "noop"`` in
``config/slice2.toml [redaction]``.

Slice 3 extensions (specs/003-real-call-real-crm/contracts/shadow-stt-lane.md
+ data-model.md §2.5 + spec.md FR-033 Round 2 Q10/Q11): the default-on policy
covers FOUR derivative artifact types — full transcript, session-result
summary, shadow STT transcript, shadow STT discrepancy records — via the
``redact_artifact_text`` helper at the end of this module. Transcript pointer
metadata is explicitly EXCLUDED (must remain machine-readable for resume).
PHI tag-and-redact runs as a pre-write pass via ``apply_phi_redaction_pass``
when the persona emits ``phi_collection_risk`` (Round 2 Q11).
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


# ---------------------------------------------------------------------------
# Slice 3 — derivative-artifact redaction (FR-033 Round 2 Q10 + Q11)
# ---------------------------------------------------------------------------

# The four artifact-text types the default-on Slice 3 redaction policy covers,
# per FR-033 amended by Round 2 Q10. Transcript pointer metadata is EXCLUDED
# (must remain machine-readable for resume). Used by ``artifacts/writer.py``
# (US1 / US6) to drive a single pre-write redaction pass against every derived
# artifact regardless of which Slice 3 module produces it.
SLICE3_REDACTABLE_ARTIFACT_KINDS: tuple[str, ...] = (
    "transcript",
    "session_result_summary",
    "shadow_transcript",
    "shadow_discrepancy_record",
)


def redact_artifact_text(
    layer: RedactionLayer,
    kind: str,
    text: str,
) -> str:
    """Apply the Slice 3 default-on redaction policy to a single artifact text.

    Pointer metadata MUST never be passed here — pointers must remain
    machine-readable for resume / inspection (Round 2 Q10). Callers that write
    ``transcript_pointer`` fields bypass redaction by construction; this helper
    only operates on the four redactable kinds enumerated above.
    """
    if kind not in SLICE3_REDACTABLE_ARTIFACT_KINDS:
        raise ValueError(
            f"redact_artifact_text() received unknown artifact kind {kind!r}; "
            f"expected one of {SLICE3_REDACTABLE_ARTIFACT_KINDS}. Pointer metadata "
            "MUST remain unredacted per FR-033 Round 2 Q10 and is intentionally "
            "not a supported kind here."
        )
    return layer.redact(text)


def apply_phi_redaction_pass(
    layer: RedactionLayer,
    *,
    transcript_text: str | None,
    summary_text: str | None,
    shadow_transcript_text: str | None,
    shadow_discrepancy_texts: list[str],
    phi_spans: list[tuple[int, int]] | None = None,  # noqa: ARG001  (reserved for US5)
) -> dict[str, str | list[str]]:
    """PHI tag-and-redact pre-write pass for caller-volunteered PHI cases.

    Spec: FR-015 amended by Round 2 Q11. When the persona module emits a
    ``phi_collection_risk`` escalation event, the orchestrator MUST invoke this
    pass on the in-flight transcript / summary / shadow transcript / shadow
    discrepancy buffer BEFORE any of those artifacts is written to disk. The
    PHI-volunteered case MUST be observably distinct from a non-PHI call in
    the audit artifacts and the run report.

    Slice 3 (T009) only wires the API shape; the concrete PHI-span detection
    and tagging lands in US5 (T066). For now the function applies the standard
    default-on redaction to every supplied artifact text so the contract test
    ``test_caller_volunteered_phi_escalates_and_redacts`` can assert the
    artifacts are at least passed through the redaction layer.
    """
    redacted: dict[str, str | list[str]] = {}
    if transcript_text is not None:
        redacted["transcript"] = redact_artifact_text(layer, "transcript", transcript_text)
    if summary_text is not None:
        redacted["summary"] = redact_artifact_text(
            layer, "session_result_summary", summary_text,
        )
    if shadow_transcript_text is not None:
        redacted["shadow_transcript"] = redact_artifact_text(
            layer, "shadow_transcript", shadow_transcript_text,
        )
    redacted["shadow_discrepancy_records"] = [
        redact_artifact_text(layer, "shadow_discrepancy_record", text)
        for text in shadow_discrepancy_texts
    ]
    return redacted
