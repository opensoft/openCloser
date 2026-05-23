"""Unit tests for Dataverse metadata verification/discovery and queue intake,
exercised against the in-process Dataverse fake (tasks T013-T016).
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
    """Build a complete fake entity/attribute map from a mapping artifact."""
    entities: dict[str, set[str]] = {}
    for ekey, eref in mapping.entities.items():
        attrs = {eref.primary_id} if eref.primary_id else set()
        attrs |= {f.logical_name for f in mapping.fields.values() if f.entity == ekey}
        entities[eref.logical_name] = attrs
    entities["account"] = {"accountid", "name"}
    return entities


def _queue_record(*, status: int = 0, attempt: int = 0, next_at: str, qid: str = _QUEUE_GUID) -> dict:
    return {
        "medx_callqueueitemid": qid,
        "medx_accountid": _ACCOUNT_GUID,
        "medx_phonenumber": "+15305551234",
        "medx_timezone": "America/Los_Angeles",
        "medx_attemptcount": attempt,
        "medx_maxattempts": 5,
        "medx_donotcall": False,
        "medx_callstatus": status,
        "medx_nextattemptat": next_at,
    }


# ---------------------------------------------------------------------------
# T013 — metadata verify / discover
# ---------------------------------------------------------------------------


def test_verify_ok_for_complete_metadata() -> None:
    fake = DataverseFake(entities=_entities(_MAPPING))
    report = verify(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is True
    assert report.missing == []
    assert report.checked_at == _NOW


def test_verify_reports_missing_entity() -> None:
    entities = _entities(_MAPPING)
    del entities["task"]  # the Task table is absent from this environment
    report = verify(DataverseFake(entities=entities).client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is False
    assert any("task" in item for item in report.missing)


def test_verify_reports_missing_field() -> None:
    entities = _entities(_MAPPING)
    entities["medx_callqueueitem"].discard("medx_callstatus")  # status column not present
    report = verify(DataverseFake(entities=entities).client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert report.ok is False
    assert any("queue.status" in item for item in report.missing)


def test_discover_refreshes_and_requires_reapproval() -> None:
    fake = DataverseFake(entities=_entities(_MAPPING))
    refreshed = discover(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)
    assert refreshed.meta.discovered_at == _NOW
    assert refreshed.meta.approved is False  # a fresh discovery needs PR re-approval
    assert refreshed.entities.keys() == _MAPPING.entities.keys()


def test_discover_raises_when_metadata_unverifiable() -> None:
    entities = _entities(_MAPPING)
    entities["medx_callqueueitem"].discard("medx_donotcall")
    fake = DataverseFake(entities=entities)
    with pytest.raises(MetadataError, match=r"queue\.dnc"):
        discover(fake.client(_RETRY), _MAPPING, now_utc_ms=_NOW)


# ---------------------------------------------------------------------------
# T014 — Dataverse queue loader
# ---------------------------------------------------------------------------


def _loader(records: dict[str, list[dict]]) -> DataverseQueueLoader:
    fake = DataverseFake(entities=_entities(_MAPPING), records=records)
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


def test_load_next_ready_filters_by_campaign_when_mapped() -> None:
    """When the mapping carries `queue.campaign`, NextReady scopes the query to
    the selector's campaign — contracts/dataverse-queue-loader.md."""
    # Augment the mapping with a campaign field (additive — extra: ignore models).
    mapping_with_campaign = _MAPPING.model_copy(deep=True)
    mapping_with_campaign.fields["queue.campaign"] = type(
        next(iter(_MAPPING.fields.values()))
    )(
        entity="queue_item",
        logical_name="medx_campaign",
        type="string",
    )
    entities = _entities(mapping_with_campaign)
    # Add campaign to known attrs so the fake $filter doesn't reject it.
    entities["medx_callqueueitem"].add("medx_campaign")
    rec_in = _queue_record(qid="q-in", next_at="2026-05-22T09:00:00.000Z")
    rec_in["medx_campaign"] = "alf-q2-davis"
    rec_out = _queue_record(qid="q-out", next_at="2026-05-22T08:00:00.000Z")
    rec_out["medx_campaign"] = "other-campaign"
    fake = DataverseFake(
        entities=entities,
        records={"medx_callqueueitem": [rec_in, rec_out], "account": [_ACCOUNT]},
    )
    loader = DataverseQueueLoader(fake.client(_RETRY), MappingTranslator(mapping_with_campaign))

    item = loader.load(NextReady("alf-q2-davis"))
    assert item is not None
    # `q-out` has an earlier next_attempt_at but is in the wrong campaign — it
    # must be excluded by the campaign filter.
    assert item.queue_item_id == "q-in"


def test_load_next_ready_unfiltered_when_campaign_unmapped() -> None:
    """If the mapping omits `queue.campaign`, the loader falls back to the
    campaign-agnostic query (the CLI gate at run-crm is the user-facing signal
    in that case — the loader does NOT silently fail)."""
    loader = _loader(
        {
            "medx_callqueueitem": [
                _queue_record(qid="q-only", next_at="2026-05-22T09:00:00.000Z")
            ],
            "account": [_ACCOUNT],
        }
    )
    item = loader.load(NextReady("any-campaign"))
    assert item is not None
    assert item.queue_item_id == "q-only"


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


def test_load_missing_account_falls_back_to_id() -> None:
    loader = _loader(
        {"medx_callqueueitem": [_queue_record(next_at="2026-05-22T16:00:00.000Z")], "account": []}
    )
    item = loader.load(ExplicitId(_QUEUE_GUID))
    assert item is not None
    assert item.facility_name == _ACCOUNT_GUID  # no Account row -> raw id fallback
