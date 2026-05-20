"""T072 — Verify .specify/memory/constitution.md remains in sync with the spec's
Constitution Alignment section. Smoke check: the 5 principle headings exist and the
file is non-empty.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_REPO = Path(__file__).resolve().parents[2]
_CONSTITUTION = _REPO / ".specify/memory/constitution.md"


def test_constitution_file_exists_and_is_non_empty() -> None:
    assert _CONSTITUTION.exists(), "Slice 1 constitution must be authored before /speckit.implement merges"
    text = _CONSTITUTION.read_text(encoding="utf-8")
    assert len(text) > 500


_PRINCIPLE_HEADINGS = (
    "Principle 1 — CRM as the conceptual control plane",
    "Principle 2 — Thin, sequenced slices",
    "Principle 3 — Five separable boundaries",
    "Principle 4 — Safety and human handoff are first-class invariants",
    "Principle 5 — Auditability and idempotency",
)


def test_constitution_lists_five_principles_in_canonical_order() -> None:
    """All five principle headings are present AND appear in canonical 1→5 order — a
    reordering or a dropped principle is a real structural regression, not just a
    missing substring."""
    text = _CONSTITUTION.read_text(encoding="utf-8")
    positions = []
    for heading in _PRINCIPLE_HEADINGS:
        idx = text.find(heading)
        assert idx != -1, f"Constitution is missing principle heading: {heading!r}"
        # Each heading is a real section header (`## Principle ...`), not prose.
        assert f"## {heading}" in text, f"{heading!r} is not a `##` section heading"
        positions.append(idx)
    assert positions == sorted(positions), (
        "Principle headings are out of canonical 1→5 order in the constitution"
    )


def test_constitution_traceability_section_references_known_FRs() -> None:
    """Each principle traces to specific FRs/SCs — checked INSIDE the `## Traceability`
    section, not merely somewhere in the file, and every principle is traced there."""
    text = _CONSTITUTION.read_text(encoding="utf-8")
    assert "## Traceability" in text, "Constitution is missing its `## Traceability` section"
    traceability = text.split("## Traceability", 1)[1]

    for fr_or_sc in (
        "FR-008", "FR-016", "FR-033", "FR-010", "FR-018",
        "FR-035", "FR-019", "FR-020", "FR-021", "SC-005", "SC-006", "SC-009",
    ):
        assert fr_or_sc in traceability, (
            f"Constitution Traceability section should mention {fr_or_sc}"
        )
    # Every one of the five principles is traced in that section.
    for n in range(1, 6):
        assert f"Principle {n}" in traceability, (
            f"Traceability section does not trace Principle {n}"
        )
