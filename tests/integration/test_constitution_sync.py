"""T072 — Verify .specify/memory/constitution.md remains in sync with the
spec's Constitution Alignment section. Smoke check: the 5 principle headings
exist and the file is non-empty.

Heading convention (Slice 1 constitution rewrite, recorded in the file's Sync
Impact Report comment): principles are titled with Roman numerals and the
short conceptual name, e.g. ``### I. CRM Is the Control Plane``. An older
test asserted the prior `## Principle 1 — CRM as the conceptual control
plane` form plus a `## Traceability` section; both went away when the
constitution was rewritten. This test was realigned by /speckit-analyze
(I1, 2026-05-25) — the structural intent (5 principles, in order) is
preserved; the Traceability-section assertion is dropped because the
rewritten constitution intentionally does NOT carry one (principle-to-FR
traceability now lives in `spec.md §Requirement Coverage Notes` and the
per-feature plan).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_REPO = Path(__file__).resolve().parents[2]
_CONSTITUTION = _REPO / ".specify/memory/constitution.md"


def test_constitution_file_exists_and_is_non_empty() -> None:
    assert _CONSTITUTION.exists(), (
        "Slice 1 constitution must be authored before /speckit.implement merges"
    )
    text = _CONSTITUTION.read_text(encoding="utf-8")
    assert len(text) > 500


# Roman-numeral + short conceptual name, as the rewritten constitution uses.
# Substring matches (not full-line) so wording tweaks inside a heading don't
# spuriously fail this structural check — the canonical-order assertion is what
# protects against a reorder or drop.
_PRINCIPLE_HEADINGS = (
    "### I. CRM Is the Control Plane",
    "### II. Thin Slices Before Platform Surface",
    "### III. Core, Adapters, and Personas Stay Separate",
    "### IV. Automation Is Auditable and Idempotent",
    "### V. Safety, Privacy, and Human Handoff Are Required Paths",
)


def test_constitution_lists_five_principles_in_canonical_order() -> None:
    """All five principle headings are present AND appear in canonical I→V
    order — a reordering or a dropped principle is a real structural
    regression, not just a missing substring."""
    text = _CONSTITUTION.read_text(encoding="utf-8")
    positions = []
    for heading in _PRINCIPLE_HEADINGS:
        idx = text.find(heading)
        assert idx != -1, f"Constitution is missing principle heading: {heading!r}"
        positions.append(idx)
    assert positions == sorted(positions), (
        "Principle headings are out of canonical I→V order in the constitution"
    )


def test_constitution_has_governance_and_architecture_sections() -> None:
    """Beyond the principles themselves, the constitution MUST carry the two
    structural sections that anchor downstream specs/plans:

      * ``## Architecture Constraints`` — what the slices are allowed to
        build on (queue/eligibility/transport/persona/result/write-back/
        human-follow-up loop) and what is out-of-scope for the MVP.
      * ``## Governance`` — the amendment + review rules.

    These replaced the old `## Traceability` section in the Slice 1 rewrite;
    every per-feature spec's `## Constitution Alignment` block points back
    at the principle text alone, not at a constitution-side trace table.
    """
    text = _CONSTITUTION.read_text(encoding="utf-8")
    for required_section in ("## Architecture Constraints", "## Governance"):
        assert required_section in text, (
            f"Constitution is missing the {required_section!r} section"
        )
