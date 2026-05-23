"""Unit tests for the Slice 2 foundational layer — models, state DAO, error
taxonomy, and configuration (tasks T005-T009).

Part of T016 (foundational-module unit tests); the mapping/client retry portions
are added with T011/T012.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from opencloser.core import config
from opencloser.crm.dataverse import errors
from opencloser.models import (
    CrmCorrelation,
    CrmRecordKind,
    CrmWriteStatus,
    DataverseMapping,
    QueueItem,
    RunMode,
    RunStatus,
    Session,
    SessionState,
    WriteBackProgress,
)
from opencloser.state import store

_REPO_ROOT = Path(__file__).parents[2]
_TS = "2026-05-22T16:00:00.000Z"


# ---------------------------------------------------------------------------
# T005 — models
# ---------------------------------------------------------------------------


def test_run_mode_values() -> None:
    assert RunMode.DRY_RUN.value == "dry-run"
    assert RunMode.WRITE_ENABLED.value == "write-enabled"


def test_dataverse_mapping_loads_verified_fixture() -> None:
    raw = json.loads(
        (_REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json").read_text("utf-8")
    )
    mapping = DataverseMapping.model_validate(raw)
    assert mapping.meta.approved is True  # the fixture mapping is a verified mapping
    assert mapping.entities["queue_item"].logical_name == "medx_callqueueitem"
    assert mapping.fields["queue.status"].approved_update_field is True
    assert mapping.fields["queue.phone"].approved_update_field is False
    assert mapping.option_sets["queue_status.ready"].value == 0
    assert "medx_notes" in mapping.preserve_if_present


# ---------------------------------------------------------------------------
# T006 + T007 — schema + DAO
# ---------------------------------------------------------------------------


def _seed_session(conn: sqlite3.Connection, session_id: str = "sess-1") -> None:
    store.insert_queue_item(
        conn,
        QueueItem(
            queue_item_id="q-1",
            facility_name="Test ALF",
            attempt_count=0,
            callable_status="ready",
        ),
    )
    store.insert_session(
        conn,
        Session(
            session_id=session_id,
            queue_item_id="q-1",
            state=SessionState.CREATED,
            started_at=_TS,
        ),
    )


def test_crm_correlation_roundtrip_and_upsert(tmp_state_db: sqlite3.Connection) -> None:
    _seed_session(tmp_state_db)
    corr = CrmCorrelation(
        session_id="sess-1",
        record_kind=CrmRecordKind.PHONE_CALL_ACTIVITY,
        idempotency_key="sess-1",
        dataverse_record_id=None,
        write_status=CrmWriteStatus.PENDING,
        created_at=_TS,
        updated_at=_TS,
    )
    store.upsert_crm_correlation(tmp_state_db, corr)
    loaded = store.get_crm_correlation(
        tmp_state_db, "sess-1", CrmRecordKind.PHONE_CALL_ACTIVITY
    )
    assert loaded == corr

    # Upsert (same PK) confirms the write and records the Dataverse GUID.
    confirmed = corr.model_copy(
        update={"write_status": CrmWriteStatus.CONFIRMED, "dataverse_record_id": "guid-9"}
    )
    store.upsert_crm_correlation(tmp_state_db, confirmed)
    reloaded = store.get_crm_correlation(
        tmp_state_db, "sess-1", CrmRecordKind.PHONE_CALL_ACTIVITY
    )
    assert reloaded is not None
    assert reloaded.write_status is CrmWriteStatus.CONFIRMED
    assert reloaded.dataverse_record_id == "guid-9"
    assert len(store.list_crm_correlations(tmp_state_db, "sess-1")) == 1


def test_writeback_progress_roundtrip(tmp_state_db: sqlite3.Connection) -> None:
    _seed_session(tmp_state_db)
    assert store.get_writeback_progress(tmp_state_db, "sess-1") is None
    progress = WriteBackProgress(
        session_id="sess-1",
        phone_call_activity_done=True,
        run_status=RunStatus.RESUME_NEEDED,
        last_error="transient write-back failure",
        updated_at=_TS,
    )
    store.upsert_writeback_progress(tmp_state_db, progress)
    loaded = store.get_writeback_progress(tmp_state_db, "sess-1")
    assert loaded == progress
    assert loaded is not None and loaded.queue_status_update_done is False


# ---------------------------------------------------------------------------
# T008 — Dataverse error taxonomy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "transient"),
    [(408, True), (429, True), (500, True), (503, True), (400, False), (404, False)],
)
def test_is_transient_status(status: int, transient: bool) -> None:
    assert errors.is_transient_status(status) is transient


def test_raise_for_dataverse_response_transient_with_retry_after() -> None:
    request = httpx.Request("PATCH", "https://fake.crm.dynamics.com/api/data/v9.2/x")
    response = httpx.Response(429, headers={"Retry-After": "7"}, request=request)
    with pytest.raises(errors.TransientDataverseError) as exc_info:
        errors.raise_for_dataverse_response(response)
    assert exc_info.value.retry_after == pytest.approx(7.0)


def test_raise_for_dataverse_response_permanent() -> None:
    request = httpx.Request("POST", "https://fake.crm.dynamics.com/api/data/v9.2/x")
    with pytest.raises(errors.PermanentDataverseError) as exc_info:
        errors.raise_for_dataverse_response(httpx.Response(404, request=request))
    assert exc_info.value.status_code == 404  # callers can narrow on 404 vs. 401/403


def test_raise_for_dataverse_response_success_is_noop() -> None:
    request = httpx.Request("GET", "https://fake.crm.dynamics.com/api/data/v9.2/x")
    errors.raise_for_dataverse_response(httpx.Response(200, request=request))


def test_wrap_transport_error_classifies_timeout_as_transient() -> None:
    wrapped = errors.wrap_transport_error(httpx.ConnectTimeout("timed out"))
    assert isinstance(wrapped, errors.TransientDataverseError)


def test_wrap_transport_error_classifies_network_error_as_transient() -> None:
    wrapped = errors.wrap_transport_error(httpx.ConnectError("refused"))
    assert isinstance(wrapped, errors.TransientDataverseError)


@pytest.mark.parametrize(
    "exc",
    [
        httpx.UnsupportedProtocol("bad scheme"),
        httpx.LocalProtocolError("bad request line"),
        httpx.ProxyError("proxy misconfig"),
    ],
)
def test_wrap_transport_error_classifies_misconfiguration_as_permanent(
    exc: httpx.HTTPError,
) -> None:
    """Misconfiguration-class transport errors cannot succeed on retry — classifying
    them as transient would burn the FR-023 retry budget on impossible requests
    (Codex review on PR #3)."""
    wrapped = errors.wrap_transport_error(exc)
    assert isinstance(wrapped, errors.PermanentDataverseError)


# ---------------------------------------------------------------------------
# T009 — Slice 2 configuration + secrets
# ---------------------------------------------------------------------------


def test_load_slice2_config() -> None:
    cfg = config.load_slice2_config(_REPO_ROOT / "config/slice2.toml")
    assert cfg.run.default_mode is RunMode.DRY_RUN
    assert cfg.dataverse.callable_status == "ready"
    assert cfg.retry.max_retries == 3
    assert cfg.retry.backoff_seconds == [1.0, 2.0, 4.0]
    assert cfg.redaction.policy == "regex"
    assert len(cfg.redaction.patterns) == 2


def test_load_slice2_config_applies_env_var_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPENCLOSER_<SECTION>_<KEY> overrides each scalar key in slice2.toml — same
    loader pattern as Slice 1 (research.md §5)."""
    monkeypatch.setenv("OPENCLOSER_DATAVERSE_CALLABLE_STATUS", "in_progress")
    monkeypatch.setenv("OPENCLOSER_RETRY_MAX_RETRIES", "7")
    monkeypatch.setenv("OPENCLOSER_RETRY_RETRY_AFTER_CAP_SECONDS", "12.5")
    monkeypatch.setenv("OPENCLOSER_REDACTION_RETENTION", "summary-only")
    cfg = config.load_slice2_config(_REPO_ROOT / "config/slice2.toml")
    assert cfg.dataverse.callable_status == "in_progress"
    assert cfg.retry.max_retries == 7
    assert cfg.retry.retry_after_cap_seconds == pytest.approx(12.5)
    assert cfg.redaction.retention == "summary-only"


def test_missing_dataverse_secrets_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in config._DATAVERSE_SECRET_ENV:
        monkeypatch.delenv(name, raising=False)
    assert sorted(config.missing_dataverse_secret_env_vars()) == sorted(
        config._DATAVERSE_SECRET_ENV
    )
    with pytest.raises(config.Slice2ConfigError, match="DATAVERSE_TENANT_ID"):
        config.load_dataverse_secrets()


def test_empty_string_dataverse_secret_treated_as_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A secret env var set to "" is just as bad as unset — both fail readiness.
    (Sourcery suggestion — explicit coverage of the empty-string case.)"""
    monkeypatch.setenv("DATAVERSE_TENANT_ID", "")  # explicitly empty
    monkeypatch.setenv("DATAVERSE_CLIENT_ID", "client-x")
    monkeypatch.setenv("DATAVERSE_CLIENT_SECRET", "secret-x")
    monkeypatch.setenv("DATAVERSE_ENV_URL", "https://fake.crm.dynamics.com")
    assert "DATAVERSE_TENANT_ID" in config.missing_dataverse_secret_env_vars()
    with pytest.raises(config.Slice2ConfigError, match="DATAVERSE_TENANT_ID"):
        config.load_dataverse_secrets()


def test_load_dataverse_secrets_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAVERSE_TENANT_ID", "tenant-x")
    monkeypatch.setenv("DATAVERSE_CLIENT_ID", "client-x")
    monkeypatch.setenv("DATAVERSE_CLIENT_SECRET", "secret-x")
    monkeypatch.setenv("DATAVERSE_ENV_URL", "https://fake.crm.dynamics.com")
    secrets = config.load_dataverse_secrets()
    assert secrets.tenant_id == "tenant-x"
    assert secrets.env_url == "https://fake.crm.dynamics.com"
