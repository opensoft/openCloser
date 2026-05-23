"""Dataverse field-mapping loader and translator — Slice 2 (FR-004, FR-016).

`load_mapping` reads and validates the documented mapping artifact
(`config/dataverse_mapping.json`). `MappingTranslator` is the sole place conceptual
Slice 1 field names are translated to Dataverse logical names and option-set values
— Dataverse vendor detail never leaves this boundary (FR-016, SC-010).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from opencloser.models import DataverseFieldRef, DataverseMapping


class MappingError(RuntimeError):
    """Raised when the mapping artifact is missing, malformed, or a lookup has no entry."""


def load_mapping(path: str | Path) -> DataverseMapping:
    """Load and validate the Dataverse mapping artifact (FR-004).

    Both JSON-decode failures and Pydantic schema-validation failures surface as
    `MappingError`, so callers (the runner, the discover-crm CLI) handle a single
    error type for "mapping artifact is wrong".
    """
    artifact = Path(path)
    if not artifact.exists():
        raise MappingError(f"mapping artifact not found: {artifact}")
    try:
        raw = json.loads(artifact.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MappingError(f"mapping artifact is not valid JSON: {exc}") from exc
    try:
        return DataverseMapping.model_validate(raw)
    except ValidationError as exc:
        raise MappingError(f"mapping artifact failed schema validation: {exc}") from exc


class MappingTranslator:
    """Translates conceptual Slice 1 fields to Dataverse logical names / option-set
    values (and back), using a loaded `DataverseMapping`."""

    def __init__(self, mapping: DataverseMapping) -> None:
        self._mapping = mapping

    @property
    def mapping(self) -> DataverseMapping:
        return self._mapping

    def is_approved(self) -> bool:
        """True when the mapping artifact has been PR-reviewed and approved (FR-024)."""
        return self._mapping.meta.approved

    def entity_logical_name(self, entity_key: str) -> str:
        """The Dataverse table logical name for a conceptual entity (e.g. `queue_item`)."""
        entity = self._mapping.entities.get(entity_key)
        if entity is None:
            raise MappingError(f"no Dataverse entity mapping for {entity_key!r}")
        return entity.logical_name

    def field(self, conceptual: str) -> DataverseFieldRef:
        """The full field mapping entry for a conceptual field name."""
        ref = self._mapping.fields.get(conceptual)
        if ref is None:
            raise MappingError(f"no Dataverse field mapping for {conceptual!r}")
        return ref

    def logical_name(self, conceptual: str) -> str:
        """The Dataverse attribute logical name for a conceptual field."""
        return self.field(conceptual).logical_name

    def option_set_value(self, option_key: str) -> int:
        """The Dataverse option-set integer for a conceptual option key
        (e.g. `queue_status.ready`)."""
        entry = self._mapping.option_sets.get(option_key)
        if entry is None:
            raise MappingError(f"no option-set mapping for {option_key!r}")
        return entry.value

    def option_set_key_for_value(self, field_conceptual: str, value: int) -> str | None:
        """Reverse lookup — the conceptual option key whose value matches, for the given
        conceptual field. Returns None when no member matches (an option-set mismatch)."""
        for key, entry in self._mapping.option_sets.items():
            if entry.field == field_conceptual and entry.value == value:
                return key
        return None

    def approved_update_logical_names(self) -> set[str]:
        """Logical names of the approved Slice 2 update fields (FR-003 — only these may
        be written)."""
        return {
            ref.logical_name for ref in self._mapping.fields.values() if ref.approved_update_field
        }

    def preserve_if_present(self) -> list[str]:
        """Logical names of high-confidence fields that MUST NOT be overwritten (FR-003)."""
        return list(self._mapping.preserve_if_present)
