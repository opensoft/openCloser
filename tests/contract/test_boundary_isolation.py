"""T040 — Boundary isolation contract (SC-010 / FR-016).

Asserts that Dataverse-specific field names, OData query syntax, and
Dataverse-specific imports do not appear in the orchestrator, eligibility
evaluator, mock transport, or persona modules. The Slice 2 Dataverse adapter
(and the supporting `crm/dataverse/` package) is the SOLE place vendor detail
may appear (FR-016).

Complementary to `tests/test_imports.py` (which enforces the import-graph
direction): this test catches leaked STRING literals and inline references
that an import check alone would miss — e.g. a stray `medx_lastsessionid`
literal that nothing imports but that still binds the boundary module to a
Dataverse-specific name.

A failure here means a vendor detail has leaked past the boundary and the
fix is to move the leaked reference into `crm/dataverse/` and route it
through the existing `MappingTranslator` / `DataverseWriteBackAdapter`
surfaces.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "opencloser"


# Modules whose source MUST NOT carry any Dataverse vendor reference.
#
# These are the four boundary modules named in FR-016 (orchestrator,
# eligibility evaluator, mock transport, persona) plus the small `core/`
# helpers the orchestrator shares with them. The Slice 1 contract surface
# names (`PhoneCallActivityPayload`, `TaskPayload`, etc.) ARE allowed here —
# those are conceptual payload Python classes, not vendor logical names.
_MODULES_UNDER_TEST: tuple[Path, ...] = (
    _SRC / "core" / "orchestrator.py",
    _SRC / "core" / "idempotency.py",
    _SRC / "core" / "ids.py",
    _SRC / "core" / "clock.py",
    _SRC / "core" / "config.py",
    _SRC / "eligibility" / "evaluator.py",
    _SRC / "transport" / "base.py",
    _SRC / "transport" / "mock.py",
    _SRC / "persona" / "base.py",
    _SRC / "persona" / "alf_appointment_setter.py",
    _SRC / "persona" / "extraction.py",
    _SRC / "persona" / "disposition_rules.py",
    _SRC / "persona" / "escalation.py",
    # Pass 2C (2026-05-24 audit-remediation): boundary-package __init__.py
    # files — a forbidden cross-boundary import or vendor-name leak must not
    # be able to hide in a package root. test_imports.py walks these for
    # the same reason; this test does the parallel text-grep check.
    _SRC / "core" / "__init__.py",
    _SRC / "eligibility" / "__init__.py",
    _SRC / "transport" / "__init__.py",
    _SRC / "persona" / "__init__.py",
)


# Each (pattern, label, description) tuple is one forbidden vendor reference
# the boundary modules MUST NOT contain.
_FORBIDDEN_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    # OData v4 query-string syntax — used only by the Dataverse Web API client.
    # Match both double- and single-quoted literals (Pass 2C — prior single-
    # quote-only patterns let a style-drift bypass the check).
    (re.compile(r"""["']\$filter["']"""), "odata-$filter", "OData query keyword"),
    (re.compile(r"""["']\$select["']"""), "odata-$select", "OData query keyword"),
    (re.compile(r"""["']\$top["']"""), "odata-$top", "OData query keyword"),
    (re.compile(r"""["']\$orderby["']"""), "odata-$orderby", "OData query keyword"),
    # Dataverse Web API response/request header — appears only in the
    # create-record POST flow inside the adapter.
    (re.compile(r"OData-EntityId"), "odata-entityid-header", "Dataverse Web API header"),
    # Pass 2C: OData binding/identity annotations. `@odata.bind` is used for
    # lookup writes (e.g. `ownerid@odata.bind`); `@odata.id` is the
    # navigation-target reference. Both belong inside the adapter.
    (re.compile(r"@odata\.bind"), "odata-bind", "OData @odata.bind navigation reference"),
    (re.compile(r"@odata\.id"), "odata-id", "OData @odata.id navigation reference"),
    # Pass 2C: Dataverse Web API URL prefix. A boundary module that built
    # `/api/data/v9.2/...` URLs would be doing Dataverse work directly.
    (re.compile(r"/api/data/v9"), "dataverse-api-prefix", "Dataverse Web API URL prefix"),
    # Dataverse activity / system entity-set names as string literals.
    # The Slice 1 contract uses CLASS names (`PhoneCallActivityPayload`) —
    # those are fine. The LOWERCASE strings below are Dataverse entity-set
    # names that should only appear inside the adapter / queue loader.
    (re.compile(r"""["']phonecalls?["']"""), "phonecall-entity-set", "Dataverse entity-set name"),
    (re.compile(r"""["']systemusers?["']"""), "systemuser-entity-set", "Dataverse entity-set name"),
    (re.compile(r"""["']\bteams?\b["']"""), "team-entity-set", "Dataverse entity-set name"),
    # Pass 2C: well-known unprefixed Dataverse logical names that often
    # appear in lookup/system fields. Real deployments use a variety of
    # publisher prefixes (medx_, msdyn_, ...); these unprefixed names are
    # built-in Dataverse system attributes that should also only appear
    # inside the adapter / queue loader.
    (re.compile(r"\bregardingobjectid\b"), "regardingobjectid", "Dataverse built-in lookup"),
    (re.compile(r"\bactivitypointer\b"), "activitypointer", "Dataverse built-in entity"),
    (re.compile(r"\bdirectioncode\b"), "directioncode", "Dataverse phonecall built-in field"),
    # Vendor logical-name prefix from the fixture mapping. Real deployments
    # may use other prefixes (medx_, msdyn_, etc.); the test fixture uses
    # `medx_` so it acts as a reliable canary for "Dataverse field name
    # has leaked past the boundary". A non-fixture deployment with a
    # different prefix should also forbid that prefix here.
    (re.compile(r"\bmedx_\w+\b"), "medx-logical-name", "Dataverse fixture logical-name prefix"),
    # Imports from the Dataverse adapter package. test_imports.py covers the
    # graph-level check; this is a belt-and-suspenders text-level check.
    (
        re.compile(r"^\s*from opencloser\.crm\.dataverse", re.MULTILINE),
        "import-crm-dataverse",
        "`from opencloser.crm.dataverse` import",
    ),
    (
        re.compile(r"^\s*import opencloser\.crm\.dataverse", re.MULTILINE),
        "import-crm-dataverse-module",
        "`import opencloser.crm.dataverse` import",
    ),
)


def test_all_boundary_modules_exist() -> None:
    """Sanity — guard the module list against silent drift (e.g. a rename
    that bypasses this test by changing the file path)."""
    missing = [m for m in _MODULES_UNDER_TEST if not m.exists()]
    assert not missing, f"expected boundary module(s) not found: {missing}"


@pytest.mark.parametrize(
    "module",
    _MODULES_UNDER_TEST,
    ids=lambda p: str(p.relative_to(_SRC)),
)
@pytest.mark.parametrize(
    ("pattern", "label", "description"),
    _FORBIDDEN_PATTERNS,
    ids=lambda v: v if isinstance(v, str) else "pat",
)
def test_no_dataverse_vendor_reference_in_boundary_module(
    module: Path, pattern: re.Pattern[str], label: str, description: str
) -> None:
    """SC-010 / FR-016 — every boundary module contains ZERO matches for the
    forbidden pattern. A match means Dataverse vendor detail has leaked past
    the boundary and the fix is to move the reference into `crm/dataverse/`."""
    text = module.read_text(encoding="utf-8")
    matches = pattern.findall(text)
    assert not matches, (
        f"{module.relative_to(_SRC)} contains forbidden {description} "
        f"(pattern {label!r}): {matches[:5]}" + (" ... [truncated]" if len(matches) > 5 else "")
    )
