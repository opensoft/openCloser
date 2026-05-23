"""Dataverse metadata discovery and verification — Slice 2 (FR-001, FR-002).

`verify` is the read-only, per-write-enabled-run guard: it confirms every mapped
entity and field still exists in live Dataverse. `discover` re-inspects metadata for
a mapping scaffold and returns a refreshed artifact for PR review (FR-004).
See specs/002-mock-call-real-crm/contracts/metadata-discovery-verification.md.
"""

from __future__ import annotations

from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.errors import PermanentDataverseError
from opencloser.models import DataverseMapping, MetadataVerificationReport


class MetadataError(RuntimeError):
    """Raised when one-time discovery cannot confirm a mapped table or field (FR-002)."""


def _option_set_values(
    client: DataverseClient, entity_logical: str, attr_logical: str
) -> set[int] | None:
    """Return the set of valid option-set integer values for a Dataverse picklist
    attribute, or None when the attribute's picklist metadata cannot be fetched
    (HTTP 404 — the attribute is missing or not a picklist)."""
    try:
        response = client.get(
            f"EntityDefinitions(LogicalName='{entity_logical}')"
            f"/Attributes(LogicalName='{attr_logical}')"
            f"/Microsoft.Dynamics.CRM.PicklistAttributeMetadata"
        )
    except PermanentDataverseError as exc:
        if exc.status_code == 404:
            return None
        raise
    options = response.json().get("OptionSet", {}).get("Options", [])
    return {opt["Value"] for opt in options if "Value" in opt}


def _entity_attributes(client: DataverseClient, logical_name: str) -> set[str] | None:
    """Return a Dataverse table's attribute logical names, or None if the table itself
    cannot be found (a 404 on its metadata).

    Only HTTP 404 is treated as "entity missing"; other `PermanentDataverseError`
    cases (400 bad request, 401/403 auth/permission, etc.) are real failures and
    propagate — they MUST NOT be silently downgraded to "missing".
    """
    try:
        client.get(f"EntityDefinitions(LogicalName='{logical_name}')")
    except PermanentDataverseError as exc:
        if exc.status_code == 404:
            return None
        raise
    response = client.get(
        f"EntityDefinitions(LogicalName='{logical_name}')/Attributes",
        params={"$select": "LogicalName"},
    )
    return {row["LogicalName"] for row in response.json().get("value", [])}


def verify(
    client: DataverseClient, mapping: DataverseMapping, *, now_utc_ms: str
) -> MetadataVerificationReport:
    """Lightweight, read-only verification that every mapped table and field still
    exists in live Dataverse (FR-001 phase 2, FR-002).

    Transient failures propagate (an unreachable Dataverse fails the run); a missing
    table or field is reported in the result, not raised.
    """
    missing: list[str] = []
    attributes_by_entity: dict[str, set[str] | None] = {}
    for entity_key, entity_ref in mapping.entities.items():
        attrs = _entity_attributes(client, entity_ref.logical_name)
        attributes_by_entity[entity_key] = attrs
        if attrs is None:
            missing.append(f"entity {entity_key!r} (table '{entity_ref.logical_name}')")

    for field_key, field_ref in mapping.fields.items():
        if field_ref.entity not in mapping.entities:
            missing.append(
                f"field {field_key!r} references unmapped entity {field_ref.entity!r}"
            )
            continue
        attrs = attributes_by_entity.get(field_ref.entity)
        if attrs is None:
            continue  # the entity is missing — already reported above
        if field_ref.logical_name not in attrs:
            missing.append(
                f"field {field_key!r} (column '{field_ref.logical_name}' "
                f"on '{mapping.entities[field_ref.entity].logical_name}')"
            )

    # Option-set value validation — for each mapped option-set member, confirm its
    # integer value is present in the live Dataverse picklist (FR-001/FR-002,
    # contracts/metadata-discovery-verification.md). Cache per attribute so each
    # picklist is only fetched once even when many option_sets share a field.
    picklist_cache: dict[tuple[str, str], set[int] | None] = {}
    for option_key, option_ref in mapping.option_sets.items():
        field_ref = mapping.fields.get(option_ref.field)
        if field_ref is None:
            missing.append(
                f"option-set {option_key!r} references unmapped field "
                f"{option_ref.field!r}"
            )
            continue
        if field_ref.entity not in mapping.entities:
            continue  # entity already reported above
        attrs = attributes_by_entity.get(field_ref.entity)
        if attrs is None or field_ref.logical_name not in attrs:
            continue  # field already reported above — picklist would 404
        entity_logical = mapping.entities[field_ref.entity].logical_name
        cache_key = (entity_logical, field_ref.logical_name)
        if cache_key not in picklist_cache:
            picklist_cache[cache_key] = _option_set_values(
                client, entity_logical, field_ref.logical_name
            )
        live_values = picklist_cache[cache_key]
        if live_values is None:
            missing.append(
                f"option-set values for {option_ref.field!r} (column "
                f"'{field_ref.logical_name}') could not be read"
            )
            continue
        if option_ref.value not in live_values:
            missing.append(
                f"option-set {option_key!r} value {option_ref.value} not present in "
                f"Dataverse picklist '{field_ref.logical_name}' "
                f"(live values: {sorted(live_values)})"
            )

    return MetadataVerificationReport(
        ok=not missing, missing=missing, drift=[], checked_at=now_utc_ms
    )


def discover(
    client: DataverseClient, scaffold: DataverseMapping, *, now_utc_ms: str
) -> DataverseMapping:
    """Re-inspect live metadata for the entities/fields of `scaffold` and return a
    refreshed mapping artifact.

    Discovery is scaffold-driven: the conceptual-to-logical field assignment is a
    human-reviewed decision (FR-004), so `discover` confirms an existing scaffold's
    schema against live Dataverse rather than inventing conceptual mappings. The
    returned artifact has a refreshed `discovered_at` and `approved` reset to False —
    a fresh discovery requires PR re-approval before write-enabled use (FR-024).
    Raises `MetadataError` when any mapped table/field cannot be confirmed.
    """
    report = verify(client, scaffold, now_utc_ms=now_utc_ms)
    if not report.ok:
        raise MetadataError(
            "metadata discovery failed — unverifiable mapping: " + "; ".join(report.missing)
        )
    refreshed = scaffold.model_copy(deep=True)
    refreshed.meta.discovered_at = now_utc_ms
    refreshed.meta.approved = False
    return refreshed
