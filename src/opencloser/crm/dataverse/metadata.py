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


# Option-set-bearing Dataverse attributes are exposed under one of several
# metadata casts. Try them in order — Picklist is the most common, Status covers
# `statuscode`-style columns whose mapping otherwise reports as missing-on-verify
# even though the attribute exists (Codex review on PR #3).
_OPTION_SET_METADATA_CASTS = (
    "Microsoft.Dynamics.CRM.PicklistAttributeMetadata",
    "Microsoft.Dynamics.CRM.StatusAttributeMetadata",
)


def _option_set_values(
    client: DataverseClient, entity_logical: str, attr_logical: str
) -> set[int] | None:
    """Return the set of valid option-set integer values for a Dataverse option-set
    attribute (Picklist or Status), or None when no option-set metadata cast resolves
    (HTTP 404 from each tried cast — the attribute is missing or not an option set).

    Values can live under either `OptionSet` (local choices) or `GlobalOptionSet`
    (referenced global choices, with `OptionSet` null) in the response payload;
    look in both buckets so a field backed by a global choice doesn't get reported
    as missing during readiness verification (Codex review on PR #3).
    """
    for cast in _OPTION_SET_METADATA_CASTS:
        try:
            response = client.get(
                f"EntityDefinitions(LogicalName='{entity_logical}')"
                f"/Attributes(LogicalName='{attr_logical}')"
                f"/{cast}"
            )
        except PermanentDataverseError as exc:
            if exc.status_code == 404:
                continue  # try the next option-set metadata cast
            raise
        body = response.json()
        options: list[dict[str, object]] = []
        for bucket_key in ("OptionSet", "GlobalOptionSet"):
            bucket = body.get(bucket_key)
            if isinstance(bucket, dict):
                bucket_options = bucket.get("Options")
                if isinstance(bucket_options, list) and bucket_options:
                    options = bucket_options
                    break
        return {opt["Value"] for opt in options if "Value" in opt}
    return None


def _entity_attributes(
    client: DataverseClient, logical_name: str
) -> tuple[set[str], str | None] | None:
    """Return `(attribute logical names, live EntitySetName)` for a Dataverse table,
    or None if the table itself cannot be found (a 404 on its metadata).

    The live EntitySetName is captured so verification can compare it against the
    mapping's `entity_set_name` (Codex review on PR #3) — a mismatch silently 404s
    every record-CRUD URL at runtime if not caught at the readiness gate.

    Only HTTP 404 is treated as "entity missing"; other `PermanentDataverseError`
    cases (400 bad request, 401/403 auth/permission, etc.) are real failures and
    propagate — they MUST NOT be silently downgraded to "missing".
    """
    try:
        entity_def = client.get(f"EntityDefinitions(LogicalName='{logical_name}')")
    except PermanentDataverseError as exc:
        if exc.status_code == 404:
            return None
        raise
    live_entity_set = entity_def.json().get("EntitySetName")
    response = client.get(
        f"EntityDefinitions(LogicalName='{logical_name}')/Attributes",
        params={"$select": "LogicalName"},
    )
    attrs = {row["LogicalName"] for row in response.json().get("value", [])}
    return attrs, live_entity_set


def _check_entities(
    client: DataverseClient, mapping: DataverseMapping
) -> tuple[dict[str, set[str] | None], list[str]]:
    """Verify every mapped entity exists AND its mapping `entity_set_name` matches
    the live `EntitySetName`; return (attributes_by_entity, missing)."""
    attributes_by_entity: dict[str, set[str] | None] = {}
    missing: list[str] = []
    for entity_key, entity_ref in mapping.entities.items():
        result = _entity_attributes(client, entity_ref.logical_name)
        if result is None:
            attributes_by_entity[entity_key] = None
            missing.append(f"entity {entity_key!r} (table '{entity_ref.logical_name}')")
            continue
        attrs, live_set = result
        attributes_by_entity[entity_key] = attrs
        # Verify entity_set_name against the live EntitySetName when the mapping
        # specifies one — a typo or drift 404s every record-CRUD URL at runtime,
        # so it MUST fail the readiness gate (Codex review on PR #3).
        expected_set = entity_ref.entity_set_name
        if expected_set and live_set and expected_set != live_set:
            missing.append(
                f"entity {entity_key!r} entity_set_name mismatch "
                f"(mapping={expected_set!r}, live={live_set!r})"
            )
    return attributes_by_entity, missing


def _check_fields(
    mapping: DataverseMapping, attributes_by_entity: dict[str, set[str] | None]
) -> list[str]:
    """Verify every mapped field's logical name appears on its entity's attribute list."""
    missing: list[str] = []
    for field_key, field_ref in mapping.fields.items():
        if field_ref.entity not in mapping.entities:
            missing.append(
                f"field {field_key!r} references unmapped entity {field_ref.entity!r}"
            )
            continue
        attrs = attributes_by_entity.get(field_ref.entity)
        if attrs is None:
            continue  # the entity is missing — already reported by _check_entities
        if field_ref.logical_name not in attrs:
            missing.append(
                f"field {field_key!r} (column '{field_ref.logical_name}' "
                f"on '{mapping.entities[field_ref.entity].logical_name}')"
            )
    return missing


def _check_option_set_values(
    client: DataverseClient,
    mapping: DataverseMapping,
    attributes_by_entity: dict[str, set[str] | None],
) -> list[str]:
    """Verify each mapped option-set integer is present in the live Dataverse picklist."""
    missing: list[str] = []
    # Cache per attribute so each picklist is only fetched once even when many
    # option_sets share a field.
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
            continue  # entity already reported by _check_entities
        attrs = attributes_by_entity.get(field_ref.entity)
        if attrs is None or field_ref.logical_name not in attrs:
            continue  # field already reported by _check_fields — picklist would 404
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
    return missing


def verify(
    client: DataverseClient, mapping: DataverseMapping, *, now_utc_ms: str
) -> MetadataVerificationReport:
    """Lightweight, read-only verification that every mapped entity, field, and
    option-set value still exists in live Dataverse (FR-001 phase 2, FR-002).

    Transient failures propagate (an unreachable Dataverse fails the run); a missing
    table or field is reported in the result, not raised.
    """
    attributes_by_entity, missing = _check_entities(client, mapping)
    missing.extend(_check_fields(mapping, attributes_by_entity))
    missing.extend(_check_option_set_values(client, mapping, attributes_by_entity))
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
