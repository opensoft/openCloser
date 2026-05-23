"""Unit tests for Dataverse metadata verification/discovery and queue intake,
exercised against the in-process Dataverse fake (tasks T013-T016).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opencloser.crm.dataverse.errors import PermanentDataverseError
from opencloser.crm.dataverse.mapping import MappingTranslator, load_mapping
from opencloser.crm.dataverse.metadata import MetadataError, discover, verify
from opencloser.crm.dataverse.queue_loader import (
    DataverseQueueLoader,
    ExplicitId,
    NextReady,
    QueueLoadError,
)
from opencloser.models import CallableStatus, DataverseMapping, RetryConfig
from tests.fixtures.dataverse.fake import DataverseFake

_MAPPING = load_mapping(Path(__file__).parents[1] / "fixtures/dataverse/dataverse_mapping.json")
_RETRY = RetryConfig(max_retries=0, backoff_seconds=[1.0], retry_after_cap_seconds=30.0)
_NOW = "2026-05-22T16:00:00.000Z"

_ACCOUNT_GUID = "a-0001"
_QUEUE_GUID = "q-0001"
_ACCOUNT = {"accountid": _ACCOUNT_GUID, "name": "Sunage ALF of Davis"}


def _entities(mapping: DataverseMapping) -> dict[str, set[str]]:
    """Build a complete fake entity/attribute map from a mapping artifact.

    For Dataverse lookup columns, both the navigation property (the bare logical
    name) AND the `_<logical>_value` computed property are real attributes in a
    live environment — the loader reads/filters via the latter, so the fake's
    attribute set must include it (Codex review on PR #3).
    """
    entities: dict[str, set[str]] = {}
    for ekey, eref in mapping.entities.items():
        attrs = {eref.primary_id} if eref.primary_id else set()
        for f in mapping.fields.values():
            if f.entity != ekey:
                continue
            attrs.add(f.logical_name)
            if f.type == "lookup":
                attrs.add(f"_{f.logical_name}_value")
        entities[eref.logical_name] = attrs
    # Ensure the account table is present even if a test deletes its mapping.
    entities.setdefault("account", set()).update({"accountid", "name"})
    return entities


def _entity_sets(mapping: DataverseMapping) -> dict[str, str]:
    """Build the fake's record-collection alias map (logical_name → entity_set_name)
    from a mapping artifact. Tests that exercise record CRUD must pass this so the
    fake recognises the entity-set URLs the loader/adapter emit."""
    return {
        eref.logical_name: eref.entity_set_name
        for eref in mapping.entities.values()
        if eref.entity_set_name
    }


def _option_sets(mapping: DataverseMapping) -> dict[tuple[str, str], set[int]]:
    """Build the fake's option-set table — (entity_logical, attr_logical) -> set of
    integer values — from a mapping artifact's `option_sets` section."""
    out: dict[tuple[str, str], set[int]] = {}
    for entry in mapping.option_sets.values():
        field_ref = mapping.fields.get(entry.field)
        if field_ref is None or field_ref.entity not in mapping.entities:
            continue
        entity_logical = mapping.entities[field_ref.entity].logical_name
        out.setdefault((entity_logical, field_ref.logical_name), set()).add(entry.value)
    return out


def _queue_record(
    *,
    status: int = 0,
    attempt: int = 0,
    next_at: str,
    qid: str = _QUEUE_GUID,
    campaign: str = "alf-q2-davis",
    created: str = "2026-05-22T00:00:00.000Z",
) -> dict:
    # Lookup column GUIDs live in the `_<logical>_value` computed property in real
    # Dataverse payloads (Codex review on PR #3); mirror that here so tests exercise
    # the live shape rather than a fake-only convenience naming.
    return {
        "medx_callqueueitemid": qid,
        "_medx_accountid_value": _ACCOUNT_GUID,
        "medx_phonenumber": "+15305551234",
        "medx_timezone": "America/Los_Angeles",
        "medx_attemptcount": attempt,
        "medx_maxattempts": 5,
        "medx_donotcall": False,
        "medx_callstatus": status,
        "medx_nextattemptat": next_at,
        "_medx_campaignid_value": campaign,
        "createdon": created,
    }


# ---------------------------------------------------------------------------
# T013 — metadata verify / discover
# ---------------------------------------------------------------------------


def test_verify_ok_for_complete_metadata() -> None:
    fake = DataverseFake(entities=_entities(_MAPPING), option_sets=_option_sets(_MAPPING), entity_sets=_entity_sets(_MAPPING))
    report = verify(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is True
    assert report.missing == []
    assert report.checked_at == _NOW


def test_verify_reports_missing_entity() -> None:
    entities = _entities(_MAPPING)
    del entities["task"]  # the Task table is absent from this environment
    report = verify(DataverseFake(entities=entities, option_sets=_option_sets(_MAPPING), entity_sets=_entity_sets(_MAPPING)).client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is False
    assert any("task" in item for item in report.missing)


def test_verify_reports_missing_field() -> None:
    entities = _entities(_MAPPING)
    entities["medx_callqueueitem"].discard("medx_callstatus")  # status column not present
    report = verify(DataverseFake(entities=entities, option_sets=_option_sets(_MAPPING), entity_sets=_entity_sets(_MAPPING)).client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is False
    assert any("queue.status" in item for item in report.missing)


def test_verify_reports_option_set_value_mismatch() -> None:
    """`verify` MUST check that every mapped option-set integer is present in the
    live Dataverse picklist (contracts/metadata-discovery-verification.md), not just
    that the field exists."""
    option_sets = _option_sets(_MAPPING)
    # Remove `ready` (0) from the medx_callstatus picklist so the mapping's
    # queue_status.ready entry no longer matches a live value.
    option_sets[("medx_callqueueitem", "medx_callstatus")].discard(0)
    fake = DataverseFake(entities=_entities(_MAPPING), option_sets=option_sets, entity_sets=_entity_sets(_MAPPING))
    report = verify(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is False
    assert any("queue_status.ready" in m for m in report.missing)


def test_verify_propagates_non_404_permanent_errors() -> None:
    """A 401/403/400 during metadata lookup is a real failure (auth/permission/bad
    request), not "entity missing" — `_entity_attributes` MUST propagate it."""
    fake = DataverseFake(entities=_entities(_MAPPING), option_sets=_option_sets(_MAPPING), entity_sets=_entity_sets(_MAPPING))
    fake.fail_next(1, status=403)  # the first metadata call gets a 403 forbidden
    with pytest.raises(PermanentDataverseError):
        verify(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)


def test_discover_refreshes_and_requires_reapproval() -> None:
    fake = DataverseFake(entities=_entities(_MAPPING), option_sets=_option_sets(_MAPPING), entity_sets=_entity_sets(_MAPPING))
    refreshed = discover(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert refreshed.meta.discovered_at == _NOW
    assert refreshed.meta.approved is False  # a fresh discovery needs PR re-approval
    assert refreshed.entities.keys() == _MAPPING.entities.keys()


def test_discover_raises_when_metadata_unverifiable() -> None:
    entities = _entities(_MAPPING)
    entities["medx_callqueueitem"].discard("medx_donotcall")
    fake = DataverseFake(entities=entities, option_sets=_option_sets(_MAPPING), entity_sets=_entity_sets(_MAPPING))
    with pytest.raises(MetadataError, match=r"queue\.dnc"):
        discover(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)


# ---------------------------------------------------------------------------
# T014 — Dataverse queue loader
# ---------------------------------------------------------------------------


def _loader(records: dict[str, list[dict]]) -> DataverseQueueLoader:
    fake = DataverseFake(
        entities=_entities(_MAPPING),
        records=records,
        option_sets=_option_sets(_MAPPING),
        entity_sets=_entity_sets(_MAPPING),
    )
    return DataverseQueueLoader(fake.client(_RETRY), MappingTranslator(_MAPPING))


def test_load_explicit_id_maps_to_queue_item_contract() -> None:
    loader = _loader(
        {
            "medx_callqueueitem": [_queue_record(next_at="2026-05-22T16:00:00.000Z")],
            "account": [_ACCOUNT],
        }
    )
    item = loader.load(ExplicitId(_QUEUE_GUID))
    assert item is not None
    assert item.queue_item_id == _QUEUE_GUID
    assert item.facility_name == "Sunage ALF of Davis"
    assert item.phone_number == "+15305551234"
    assert item.callable_status is CallableStatus.READY
    assert item.attempt_count == 0
    assert item.dnc_flag is False


def test_load_next_ready_is_deterministic() -> None:
    loader = _loader(
        {
            "medx_callqueueitem": [
                _queue_record(qid="q-late", next_at="2026-05-22T18:00:00.000Z"),
                _queue_record(qid="q-early", next_at="2026-05-22T09:00:00.000Z"),
            ],
            "account": [_ACCOUNT],
        }
    )
    item = loader.load(NextReady("alf-q2-davis"))
    assert item is not None
    assert item.queue_item_id == "q-early"  # earliest next_attempt_at wins


def test_load_next_ready_honors_campaign_filter() -> None:
    """FR-009 single-campaign scoping — a queue item in a different campaign MUST NOT
    be returned even when its next_attempt_at is earlier."""
    loader = _loader(
        {
            "medx_callqueueitem": [
                _queue_record(
                    qid="q-other-camp",
                    next_at="2026-05-22T08:00:00.000Z",
                    campaign="other-camp",
                ),
                _queue_record(
                    qid="q-mine",
                    next_at="2026-05-22T16:00:00.000Z",
                    campaign="alf-q2-davis",
                ),
            ],
            "account": [_ACCOUNT],
        }
    )
    item = loader.load(NextReady("alf-q2-davis"))
    assert item is not None
    assert item.queue_item_id == "q-mine"  # earlier other-campaign row filtered out


def test_load_next_ready_uses_created_at_tiebreaker() -> None:
    """FR-008 deterministic ordering — when next_attempt_at ties, the older CRM-created
    timestamp wins."""
    same_time = "2026-05-22T16:00:00.000Z"
    loader = _loader(
        {
            "medx_callqueueitem": [
                _queue_record(
                    qid="q-newer", next_at=same_time, created="2026-05-20T00:00:00.000Z"
                ),
                _queue_record(
                    qid="q-older", next_at=same_time, created="2026-05-15T00:00:00.000Z"
                ),
            ],
            "account": [_ACCOUNT],
        }
    )
    item = loader.load(NextReady("alf-q2-davis"))
    assert item is not None
    assert item.queue_item_id == "q-older"  # older createdon wins on tie


def test_load_next_ready_uses_configured_callable_status() -> None:
    """FR-011 — the configured callable status MUST drive next-ready selection, not a
    hardcoded `ready` value."""
    loader_args_in_progress = {
        "medx_callqueueitem": [
            _queue_record(qid="q-ready", status=0, next_at="2026-05-22T08:00:00.000Z"),
            _queue_record(qid="q-inprog", status=1, next_at="2026-05-22T16:00:00.000Z"),
        ],
        "account": [_ACCOUNT],
    }
    fake = DataverseFake(
        entities=_entities(_MAPPING),
        records=loader_args_in_progress,
        option_sets=_option_sets(_MAPPING),
        entity_sets=_entity_sets(_MAPPING),
    )
    loader = DataverseQueueLoader(
        fake.client(_RETRY), MappingTranslator(_MAPPING), callable_status="in_progress"
    )
    item = loader.load(NextReady("alf-q2-davis"))
    assert item is not None
    assert item.queue_item_id == "q-inprog"  # the configured callable status wins


def test_load_empty_queue_returns_none() -> None:
    loader = _loader({"medx_callqueueitem": [], "account": [_ACCOUNT]})
    assert loader.load(ExplicitId("does-not-exist")) is None
    assert loader.load(NextReady("alf-q2-davis")) is None


def test_load_returns_non_callable_item_for_eligibility_to_block() -> None:
    # status 3 == blocked; the loader still returns it so the eligibility evaluator
    # records the FR-011 blocked result rather than the loader hiding it.
    loader = _loader(
        {
            "medx_callqueueitem": [
                _queue_record(status=3, next_at="2026-05-22T16:00:00.000Z")
            ],
            "account": [_ACCOUNT],
        }
    )
    item = loader.load(ExplicitId(_QUEUE_GUID))
    assert item is not None
    assert item.callable_status is CallableStatus.BLOCKED


def test_load_unmapped_status_raises() -> None:
    loader = _loader(
        {
            "medx_callqueueitem": [
                _queue_record(status=99, next_at="2026-05-22T16:00:00.000Z")
            ],
            "account": [_ACCOUNT],
        }
    )
    with pytest.raises(QueueLoadError, match="option-set"):
        loader.load(ExplicitId(_QUEUE_GUID))


def test_load_explicit_id_rejects_unsafe_odata_token() -> None:
    """An id containing OData reserved characters MUST be rejected before it can
    inject into the `$filter` (defensive — Dataverse expects GUIDs, but the
    selector takes a string)."""
    loader = _loader(
        {"medx_callqueueitem": [_queue_record(next_at="2026-05-22T16:00:00.000Z")], "account": []}
    )
    with pytest.raises(QueueLoadError, match="unsafe OData"):
        loader.load(ExplicitId("foo' or 1 eq 1"))


def test_load_next_ready_rejects_unsafe_campaign_token() -> None:
    """Same defensive validation on the campaign filter value."""
    loader = _loader(
        {"medx_callqueueitem": [_queue_record(next_at="2026-05-22T16:00:00.000Z")], "account": []}
    )
    with pytest.raises(QueueLoadError, match="unsafe OData"):
        loader.load(NextReady("bad') or (1 eq 1"))


def test_load_next_ready_rejects_empty_campaign_when_mapped() -> None:
    """When the mapping defines `queue.campaign`, an empty campaign selector would
    silently widen across all campaigns; reject it instead (Codex review on PR #3)."""
    loader = _loader(
        {"medx_callqueueitem": [_queue_record(next_at="2026-05-22T16:00:00.000Z")]}
    )
    with pytest.raises(QueueLoadError, match="non-empty campaign"):
        loader.load(NextReady(""))


def _string_campaign_loader(campaign_value: str) -> DataverseQueueLoader:
    """A loader whose mapping types `queue.campaign` as a plain string column (not
    a lookup), with the seeded row's campaign set to `campaign_value`. Used to
    exercise the type-aware OData string-literal path."""
    mapping = _MAPPING.model_copy(deep=True)
    mapping.fields["queue.campaign"] = mapping.fields["queue.campaign"].model_copy(
        update={"type": "string", "lookup_target": None}
    )
    row = _queue_record(next_at="2026-05-22T16:00:00.000Z")
    row.pop("_medx_campaignid_value", None)
    row["medx_campaignid"] = campaign_value
    fake = DataverseFake(
        entities=_entities(mapping),
        records={"medx_callqueueitem": [row], "account": [_ACCOUNT]},
        option_sets=_option_sets(mapping),
        entity_sets=_entity_sets(mapping),
    )
    return DataverseQueueLoader(fake.client(_RETRY), MappingTranslator(mapping))


def test_load_next_ready_quotes_string_typed_campaign_field() -> None:
    """When `queue.campaign` is mapped as a plain string column (not a lookup), the
    filter RHS must be `'value'`, not a bare token — otherwise the OData predicate
    is invalid (Codex review on PR #3)."""
    loader = _string_campaign_loader("alf-q2-davis")
    item = loader.load(NextReady("alf-q2-davis"))
    assert item is not None and item.queue_item_id == _QUEUE_GUID


@pytest.mark.parametrize(
    "campaign_value",
    [
        "ALF Q2 Davis",     # space — common in display names
        "alf.q2.davis",     # period — also common
        "It's Davis",       # apostrophe — must be escaped (' → '')
    ],
)
def test_load_next_ready_string_campaign_accepts_common_characters(
    campaign_value: str,
) -> None:
    """String-typed campaign values legitimately contain spaces, periods, and
    apostrophes. The OData string-literal path must accept them (escaping `'` as
    `''` per spec) — the strict `[A-Za-z0-9_-]` token validator was wrong here
    (Codex follow-up review on PR #3)."""
    loader = _string_campaign_loader(campaign_value)
    item = loader.load(NextReady(campaign_value))
    assert item is not None and item.queue_item_id == _QUEUE_GUID


def test_verify_reports_entity_set_name_mismatch() -> None:
    """A mapping `entity_set_name` that doesn't match the live `EntitySetName` is
    silent runtime poison — every record CRUD URL 404s after startup. The
    readiness gate MUST catch it (Codex PR #3 P1 review)."""
    # Swap the queue_item entity_set in the fake to something different from what
    # the mapping says, simulating drift between artifact and live environment.
    entity_sets = dict(_entity_sets(_MAPPING))
    entity_sets["medx_callqueueitem"] = "medx_typoed_set_name"
    fake = DataverseFake(
        entities=_entities(_MAPPING),
        option_sets=_option_sets(_MAPPING),
        entity_sets=entity_sets,
    )
    report = verify(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is False
    assert any("entity_set_name mismatch" in m for m in report.missing)
    assert any("medx_typoed_set_name" in m for m in report.missing)


def test_verify_supports_global_option_set_values() -> None:
    """A mapped field whose option-set values live in a referenced GlobalOptionSet
    (instead of a local OptionSet) must verify successfully — otherwise every
    global-choice deployment fails readiness with false-missing entries
    (Codex PR #3 review)."""
    picklist_only = _option_sets(_MAPPING)
    global_only = {
        ("medx_callqueueitem", "medx_callstatus"): picklist_only.pop(
            ("medx_callqueueitem", "medx_callstatus")
        )
    }
    fake = DataverseFake(
        entities=_entities(_MAPPING),
        option_sets=picklist_only,            # no local OptionSet for medx_callstatus
        global_option_sets=global_only,       # but GlobalOptionSet carries the values
        entity_sets=_entity_sets(_MAPPING),
    )
    report = verify(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is True
    assert report.missing == []


def test_verify_succeeds_when_option_set_is_only_a_status_attribute() -> None:
    """A Dataverse `Status` attribute exposes its OptionSet under the
    StatusAttributeMetadata cast, not the Picklist cast. `_option_set_values` MUST
    fall back to Status when Picklist 404s, otherwise mapped status fields would be
    reported as missing on every verify (Codex review on PR #3)."""
    picklist_only = _option_sets(_MAPPING)
    status_only = {
        ("medx_callqueueitem", "medx_callstatus"): picklist_only.pop(
            ("medx_callqueueitem", "medx_callstatus")
        )
    }
    fake = DataverseFake(
        entities=_entities(_MAPPING),
        option_sets=picklist_only,  # no Picklist for medx_callstatus
        status_option_sets=status_only,  # but Status carries the values
        entity_sets=_entity_sets(_MAPPING),
    )
    report = verify(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is True
    assert report.missing == []


def test_load_next_ready_uses_lookup_value_property_for_campaign_filter() -> None:
    """Dataverse one-to-many filtering goes through the lookup's `_<logical>_value`
    computed property, not the bare logical name; otherwise live runs miss every
    record (Codex review on PR #3). Verify by seeding a row whose campaign GUID
    appears under the lookup-value property (as real Dataverse does)."""
    loader = _loader(
        {
            "medx_callqueueitem": [
                _queue_record(qid="q-x", next_at="2026-05-22T16:00:00.000Z")
            ],
            "account": [_ACCOUNT],
        }
    )
    item = loader.load(NextReady("alf-q2-davis"))
    assert item is not None and item.queue_item_id == "q-x"


def test_load_missing_facility_mapping_returns_empty() -> None:
    """A mapping that omits `queue.facility_account` is accepted; facility_name
    defaults to "" rather than raising. (Sourcery suggestion — exercise the
    `_facility_name` MappingError fallback path.)"""
    mapping = _MAPPING.model_copy(deep=True)
    del mapping.fields["queue.facility_account"]
    fake = DataverseFake(
        entities=_entities(mapping),
        records={"medx_callqueueitem": [_queue_record(next_at="2026-05-22T16:00:00.000Z")]},
        option_sets=_option_sets(mapping),
        entity_sets=_entity_sets(mapping),
    )
    loader = DataverseQueueLoader(fake.client(_RETRY), MappingTranslator(mapping))
    item = loader.load(ExplicitId(_QUEUE_GUID))
    assert item is not None
    assert item.facility_name == ""


def test_load_missing_account_falls_back_to_id() -> None:
    loader = _loader(
        {"medx_callqueueitem": [_queue_record(next_at="2026-05-22T16:00:00.000Z")], "account": []}
    )
    item = loader.load(ExplicitId(_QUEUE_GUID))
    assert item is not None
    assert item.facility_name == _ACCOUNT_GUID  # no Account row -> raw id fallback
