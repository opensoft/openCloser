"""Shared Dataverse fake setup helpers for Slice 2 tests."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from opencloser.models import DataverseMapping
from tests.fixtures.dataverse.fake import DataverseFake

_ACTIVITY_BASE_FIELDS: dict[str, set[str]] = {
    "phone_call_activity": {"subject", "description", "actualstart", "actualend", "activityid"},
    "task": {"subject", "description", "ownerid", "activityid"},
}


def entity_attributes(mapping: DataverseMapping) -> dict[str, set[str]]:
    """Build fake metadata attributes from a Dataverse mapping artifact."""
    entities: dict[str, set[str]] = {}
    for ekey, eref in mapping.entities.items():
        primary_id = eref.primary_id or f"{eref.logical_name}id"
        attrs = {primary_id}
        for field in mapping.fields.values():
            if field.entity != ekey:
                continue
            attrs.add(field.logical_name)
            if field.type == "lookup":
                attrs.add(f"_{field.logical_name}_value")
        attrs.update(_ACTIVITY_BASE_FIELDS.get(ekey, set()))
        entities[eref.logical_name] = attrs

    queue_ref = mapping.entities.get("queue_item")
    if queue_ref is not None:
        if mapping.task_owner_override_field:
            entities.setdefault(queue_ref.logical_name, set()).add(
                mapping.task_owner_override_field
            )
        # T045 — preserve_if_present logical names are queue_item fields that
        # the deployment knows exist (the adapter's `_check_conflict` $selects
        # them before the final PATCH); register them on the fake so the
        # strict $select validator doesn't 400 on a known-good check.
        if mapping.preserve_if_present:
            entities.setdefault(queue_ref.logical_name, set()).update(
                mapping.preserve_if_present
            )

    entities.setdefault("account", set()).update({"accountid", "name"})
    entities.setdefault("systemuser", set()).update({"systemuserid", "isdisabled"})
    entities.setdefault("team", set()).add("teamid")
    return entities


def entity_sets(mapping: DataverseMapping) -> dict[str, str]:
    """Build the fake's logical-name to entity-set-name alias table."""
    out = {
        eref.logical_name: eref.entity_set_name
        for eref in mapping.entities.values()
        if eref.entity_set_name
    }
    out.update({"systemuser": "systemusers", "team": "teams"})
    return out


def option_sets(mapping: DataverseMapping) -> dict[tuple[str, str], set[int]]:
    """Build the fake's option-set value table from mapping option entries."""
    out: dict[tuple[str, str], set[int]] = {}
    for entry in mapping.option_sets.values():
        field_ref = mapping.fields.get(entry.field)
        if field_ref is None or field_ref.entity not in mapping.entities:
            continue
        entity_logical = mapping.entities[field_ref.entity].logical_name
        out.setdefault((entity_logical, field_ref.logical_name), set()).add(entry.value)
    return out


def fake_for_mapping(
    mapping: DataverseMapping,
    records: dict[str, list[dict[str, Any]]] | None = None,
    *,
    entities: dict[str, Iterable[str]] | None = None,
    option_set_values: dict[tuple[str, str], Iterable[int]] | None = None,
    status_option_set_values: dict[tuple[str, str], Iterable[int]] | None = None,
    global_option_set_values: dict[tuple[str, str], Iterable[int]] | None = None,
    entity_set_values: dict[str, str] | None = None,
) -> DataverseFake:
    """Create a DataverseFake using mapping-derived defaults with override hooks."""
    return DataverseFake(
        entities=entities if entities is not None else entity_attributes(mapping),
        records=records,
        option_sets=option_set_values if option_set_values is not None else option_sets(mapping),
        status_option_sets=status_option_set_values,
        global_option_sets=global_option_set_values,
        entity_sets=entity_set_values if entity_set_values is not None else entity_sets(mapping),
    )
