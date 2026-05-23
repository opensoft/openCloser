"""Unit tests for the transcript RedactionLayer (FR-028, FR-029, FR-030, SC-009).

Covers the contract in
``specs/002-mock-call-real-crm/contracts/redaction-layer.md`` — default-on regex
policy with ``[REDACTED]`` replacement, no-op policy preserving transcript bytes,
summary-only retention, and readiness failure for a malformed redaction pattern.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opencloser.artifacts.writer import write_session_artifacts
from opencloser.models import BUILTIN_REDACTION_PATTERNS, RedactionPolicyConfig
from opencloser.redaction.layer import (
    DEFAULT_REPLACEMENT,
    NoOpPolicy,
    RedactionLayer,
    RegexRedactionPolicy,
)
from tests.fixtures.artifact_inputs import make_artifact_inputs

pytestmark = pytest.mark.module("redaction")

_TRANSCRIPT_WITH_PII = (
    "[persona] Could I confirm the best callback number?\n"
    "[contact] Sure, it's 555-123-4567 and email alice@example.com.\n"
)


# ---------------------------------------------------------------------------
# RedactionLayer construction & policy behavior
# ---------------------------------------------------------------------------


def test_default_layer_redacts_emails_and_phone_numbers() -> None:
    layer = RedactionLayer.default()
    text = "Call me at 555-123-4567 or email me at ok@example.com."
    out = layer.redact(text)
    assert "555-123-4567" not in out
    assert "ok@example.com" not in out
    assert DEFAULT_REPLACEMENT in out
    assert layer.retention_mode() == "full"


@pytest.mark.parametrize(
    "raw,expected_redactions",
    [
        ("Call (555) 123-4567 back.", 1),
        ("Try 555.123.4567 or +1 555 123 4567.", 2),
        ("ping bob@example.org and alice@example.co.uk", 2),
        # Privacy-conservative: bare 10-digit phone numbers are also redacted.
        ("Phone 5551234567 bare digits.", 1),
    ],
)
def test_regex_policy_match_variants(raw: str, expected_redactions: int) -> None:
    # Exercise the built-in defaults (email + NA phone) as they ship in the config.
    policy = RegexRedactionPolicy.from_patterns(BUILTIN_REDACTION_PATTERNS)
    out = policy.redact(raw)
    assert out.count(DEFAULT_REPLACEMENT) == expected_redactions


def test_noop_policy_returns_text_unchanged() -> None:
    layer = RedactionLayer(policy=NoOpPolicy(), _retention_mode="full")
    text = "Call me at 555-123-4567 or email ok@example.com."
    assert layer.redact(text) == text
    assert layer.retention_mode() == "full"


def test_from_config_regex_default() -> None:
    cfg = RedactionPolicyConfig()  # policy="regex", retention="full" defaults
    layer = RedactionLayer.from_config(cfg)
    assert layer.retention_mode() == "full"
    assert isinstance(layer.policy, RegexRedactionPolicy)
    assert DEFAULT_REPLACEMENT in layer.redact("555-123-4567")


def test_from_config_noop_explicit() -> None:
    cfg = RedactionPolicyConfig(policy="noop", retention="full")
    layer = RedactionLayer.from_config(cfg)
    assert isinstance(layer.policy, NoOpPolicy)
    assert layer.redact("555-123-4567") == "555-123-4567"


def test_from_config_summary_only_retention() -> None:
    cfg = RedactionPolicyConfig(policy="regex", retention="summary-only")
    layer = RedactionLayer.from_config(cfg)
    assert layer.retention_mode() == "summary-only"


def test_from_config_user_patterns_replace_builtins() -> None:
    """An explicit ``patterns`` list replaces the built-in defaults — config + code
    stay aligned by giving the regex policy exactly what the operator configured.
    To keep the built-ins, callers must include them explicitly (or omit ``patterns``
    entirely so the field default supplies them)."""
    cfg = RedactionPolicyConfig(policy="regex", patterns=[r"SECRET-\d{4}"])
    layer = RedactionLayer.from_config(cfg)
    out = layer.redact("token SECRET-1234 and phone 555-123-4567")
    # Only the user pattern matches; the built-in phone pattern is not silently applied.
    assert out.count(DEFAULT_REPLACEMENT) == 1
    assert "555-123-4567" in out


def test_from_config_user_patterns_can_extend_builtins() -> None:
    """When operators want built-ins + extras, they spell that out via
    ``BUILTIN_REDACTION_PATTERNS`` in their config — predictable composition."""
    cfg = RedactionPolicyConfig(
        policy="regex",
        patterns=[*BUILTIN_REDACTION_PATTERNS, r"SECRET-\d{4}"],
    )
    layer = RedactionLayer.from_config(cfg)
    out = layer.redact("token SECRET-1234 and phone 555-123-4567")
    assert out.count(DEFAULT_REPLACEMENT) == 2


def test_malformed_redaction_pattern_fails_readiness() -> None:
    """SC-009: a malformed redaction policy fails readiness — surfaced as a ValueError
    raised when the layer is built from config (the orchestrator wraps this as a
    readiness failure)."""
    bad_cfg = RedactionPolicyConfig(policy="regex", patterns=["(unclosed"])
    with pytest.raises(ValueError, match="Invalid redaction regex"):
        RedactionLayer.from_config(bad_cfg)


# ---------------------------------------------------------------------------
# Writer integration
# ---------------------------------------------------------------------------


def test_writer_redacts_transcript_under_regex_policy(tmp_artifact_dir: Path) -> None:
    """FR-028: with regex policy + full retention, written transcript contains
    ``[REDACTED]`` and not the original PII; the Slice 1 session-result contract
    (summary + transcript pointer) is preserved."""
    session_id = "ses_red_1"
    layer = RedactionLayer.from_config(RedactionPolicyConfig())  # regex / full defaults
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=layer,
        **make_artifact_inputs(session_id, transcript_text=_TRANSCRIPT_WITH_PII),
    )
    assert paths.transcript is not None and paths.transcript.exists()
    content = paths.transcript.read_text(encoding="utf-8")
    assert "555-123-4567" not in content
    assert "alice@example.com" not in content
    assert DEFAULT_REPLACEMENT in content
    sr = json.loads(paths.session_result.read_text(encoding="utf-8"))
    assert sr["transcript_pointer"] == "transcript.txt"


def test_writer_summary_only_retention_omits_transcript(tmp_artifact_dir: Path) -> None:
    """FR-030: summary-only retention writes NO transcript file; session-result
    summary is emitted and its ``transcript_pointer`` is null (no dangling pointer)."""
    session_id = "ses_red_2"
    layer = RedactionLayer.from_config(
        RedactionPolicyConfig(policy="regex", retention="summary-only")
    )
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=layer,
        **make_artifact_inputs(session_id, transcript_text=_TRANSCRIPT_WITH_PII),
    )
    assert paths.transcript is None
    assert not (tmp_artifact_dir / session_id / "transcript.txt").exists()
    sr = json.loads(paths.session_result.read_text(encoding="utf-8"))
    assert sr["summary"].startswith("Decision-maker confirmed interested")
    assert sr["transcript_pointer"] is None


def test_writer_noop_policy_preserves_slice1_contract(tmp_artifact_dir: Path) -> None:
    """FR-029: no-op policy + full retention writes the transcript byte-identically
    to the original (Slice 1 unredacted contract)."""
    session_id = "ses_noop"
    noop_layer = RedactionLayer(policy=NoOpPolicy(), _retention_mode="full")
    inputs = make_artifact_inputs(session_id, transcript_text=_TRANSCRIPT_WITH_PII)

    write_session_artifacts(
        artifact_root=tmp_artifact_dir / "noop",
        session_id=session_id,
        redaction_layer=noop_layer,
        **inputs,
    )
    noop_bytes = (tmp_artifact_dir / "noop" / session_id / "transcript.txt").read_bytes()

    transcript_in = inputs["transcript_text"]
    assert isinstance(transcript_in, str)
    expected = transcript_in if transcript_in.endswith("\n") else transcript_in + "\n"
    assert noop_bytes == expected.encode("utf-8")
