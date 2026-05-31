"""T013b — Rejected-by-authentication audit log contract test.

Implements the 8 assertions enumerated in
``specs/003-real-call-real-crm/contracts/rejected-auth-audit-log.md`` lines 94-103.

Patterns reuse T013's clarification answers (see
``t013-clarify-questions.md``):

- Q5 (B) — TDD red is assertion-time via the ``NotImplementedError`` stubs
  in ``src/opencloser/artifacts/rejected_auth_log.py``. T032 replaces the
  bodies and these tests turn green.
- Q6 (B) — strict pytest-asyncio (the log surface is sync; tests are sync).
- Q7 (A + B together for T013b) — the rejected-auth contract requires BOTH
  JSONL and SQLite per the contract's "On-disk file" + "SQLite mirror"
  sections, so tests inspect both surfaces.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from opencloser.artifacts.rejected_auth_log import RejectedAuthCallbackLog

# ----------------------------------------------------------------------------
# Helpers / fixtures
# ----------------------------------------------------------------------------

# Sentinel string the test asserts NEVER appears in any stored row or file.
# Mirrors the "MUST NOT log secret" guarantee from FR-008 / Round 2 Q9.
SIGNALWIRE_SIGNING_SECRET_SENTINEL = "T013B-SECRET-MARKER-must-not-appear"

# A representative callback body the tests pass through as if the receiver
# had it in hand. The contract requires it MUST NOT be stored (Round 2 Q9,
# defense in depth).
FORGED_CALLBACK_BODY_SENTINEL = "T013B-BODY-MARKER-CallStatus=completed"


@pytest.fixture
def artifacts_root(tmp_path: Path) -> Path:
    """An isolated artifacts directory per test."""
    root = tmp_path / "artifacts"
    root.mkdir()
    return root


@pytest.fixture
def state_db_path(tmp_path: Path) -> Path:
    """An isolated SQLite DB per test, pre-seeded with the
    ``rejected_auth_callbacks`` table from ``state/schema.sql``."""
    db_path = tmp_path / "state.db"
    repo_schema = Path(__file__).resolve().parents[2] / "src" / "opencloser" / "state" / "schema.sql"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(repo_schema.read_text(encoding="utf-8"))
    return db_path


@pytest.fixture
def rejected_auth_log(artifacts_root: Path, state_db_path: Path) -> RejectedAuthCallbackLog:
    return RejectedAuthCallbackLog(artifacts_root=artifacts_root, db_path=state_db_path)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ----------------------------------------------------------------------------
# Assertion 1 — record() appends to BOTH SQLite and JSONL
# ----------------------------------------------------------------------------


def test_record_appends_row(
    rejected_auth_log: RejectedAuthCallbackLog,
    artifacts_root: Path,
    state_db_path: Path,
) -> None:
    """``record(...)`` appends to both the SQLite table and the JSONL file."""
    session_id = "sess-t013b-001"
    rejected_auth_log.record(
        received_at=datetime(2026, 5, 25, 14, 0, 0, tzinfo=timezone.utc),
        session_id=session_id,
        source_metadata={"remote_addr": "203.0.113.5", "sw_source": "ws-fake"},
        http_status=401,
    )

    # JSONL surface
    jsonl_path = artifacts_root / session_id / "rejected_auth_callbacks.jsonl"
    assert jsonl_path.exists(), f"expected JSONL artifact at {jsonl_path}"
    rows = _read_jsonl(jsonl_path)
    assert len(rows) == 1

    # SQLite mirror
    with sqlite3.connect(state_db_path) as conn:
        sql_rows = conn.execute(
            "SELECT session_id, http_status FROM rejected_auth_callbacks WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    assert len(sql_rows) == 1
    assert sql_rows[0][1] == 401


# ----------------------------------------------------------------------------
# Assertion 2 — distinct from callbacks audit log
# ----------------------------------------------------------------------------


def test_distinct_from_callbacks_audit_log(
    rejected_auth_log: RejectedAuthCallbackLog,
    artifacts_root: Path,
) -> None:
    """Rows appear in ``rejected_auth_callbacks.jsonl``, NOT in
    ``callbacks_audit.jsonl`` (Round 2 Q9 — distinct audit surfaces)."""
    session_id = "sess-t013b-002"
    rejected_auth_log.record(
        received_at=datetime(2026, 5, 25, 14, 1, 0, tzinfo=timezone.utc),
        session_id=session_id,
        source_metadata={"remote_addr": "198.51.100.7"},
    )

    callbacks_audit = artifacts_root / session_id / "callbacks_audit.jsonl"
    assert not callbacks_audit.exists(), (
        f"rejected-auth events MUST NOT be written to callbacks_audit.jsonl; "
        f"found one at {callbacks_audit}"
    )

    rejected_log = artifacts_root / session_id / "rejected_auth_callbacks.jsonl"
    assert rejected_log.exists(), f"rejected-auth event missing from {rejected_log}"


# ----------------------------------------------------------------------------
# Assertion 3 — schema excludes secret and body
# ----------------------------------------------------------------------------


def test_schema_excludes_secret_and_body(
    rejected_auth_log: RejectedAuthCallbackLog,
    artifacts_root: Path,
    state_db_path: Path,
) -> None:
    """Inspecting any stored row contains 0 substrings matching the signing
    secret or the callback body fixture (FR-008, FR-035, SC-018)."""
    session_id = "sess-t013b-003"
    # The caller intentionally does NOT pass body / secret — but if a future
    # bug leaked them through `source_metadata`, this test would catch it.
    rejected_auth_log.record(
        received_at=datetime(2026, 5, 25, 14, 2, 0, tzinfo=timezone.utc),
        session_id=session_id,
        source_metadata={
            "remote_addr": "192.0.2.42",
            "sw_source": "ws-test",
            # Intentionally include a sentinel that a buggy call site might
            # have passed through. The log MUST scrub or refuse anything
            # that looks like body/secret content.
            "echoed_body_for_test": FORGED_CALLBACK_BODY_SENTINEL,
        },
    )

    jsonl_path = artifacts_root / session_id / "rejected_auth_callbacks.jsonl"
    jsonl_blob = jsonl_path.read_text(encoding="utf-8")

    with sqlite3.connect(state_db_path) as conn:
        sql_rows = conn.execute(
            "SELECT source_metadata_json FROM rejected_auth_callbacks WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    sql_blob = "\n".join(row[0] for row in sql_rows)

    for blob, label in [(jsonl_blob, "JSONL"), (sql_blob, "SQLite")]:
        assert SIGNALWIRE_SIGNING_SECRET_SENTINEL not in blob, (
            f"signing secret leaked into {label} rejected-auth row"
        )
        # The body sentinel test passes when T032 implements the scrub-or-refuse
        # behavior; T013b drives the assertion now.
        assert FORGED_CALLBACK_BODY_SENTINEL not in blob, (
            f"callback body leaked into {label} rejected-auth row; "
            f"T032 implementation must scrub or refuse body content per Round 2 Q9"
        )


# ----------------------------------------------------------------------------
# Assertion 4 — unassociated callback → session_id null + _unassociated path
# ----------------------------------------------------------------------------


def test_unassociated_callback_session_id_null(
    rejected_auth_log: RejectedAuthCallbackLog,
    artifacts_root: Path,
    state_db_path: Path,
) -> None:
    """A forged callback that cannot be matched to a known session has
    ``session_id=null`` and lands in ``artifacts/_unassociated/...``."""
    rejected_auth_log.record(
        received_at=datetime(2026, 5, 25, 14, 3, 0, tzinfo=timezone.utc),
        session_id=None,
        source_metadata={"remote_addr": "203.0.113.99"},
    )

    unassoc_path = artifacts_root / "_unassociated" / "rejected_auth_callbacks.jsonl"
    assert unassoc_path.exists(), f"unassociated callback MUST land at {unassoc_path}"
    rows = _read_jsonl(unassoc_path)
    assert any(row.get("session_id") is None for row in rows), (
        "expected at least one row with session_id=null in the unassociated log"
    )

    with sqlite3.connect(state_db_path) as conn:
        null_count = conn.execute(
            "SELECT COUNT(*) FROM rejected_auth_callbacks WHERE session_id IS NULL"
        ).fetchone()[0]
    assert null_count >= 1, "SQLite mirror missing the unassociated row"


# ----------------------------------------------------------------------------
# Assertion 5 — http_status=401 + CHECK constraint
# ----------------------------------------------------------------------------


def test_http_status_is_401(
    rejected_auth_log: RejectedAuthCallbackLog,
    state_db_path: Path,
) -> None:
    """All recorded rows have ``http_status=401``; the SQLite CHECK
    constraint enforces it for any direct INSERT."""
    rejected_auth_log.record(
        received_at=datetime(2026, 5, 25, 14, 4, 0, tzinfo=timezone.utc),
        session_id="sess-t013b-005",
        source_metadata={},
    )

    with sqlite3.connect(state_db_path) as conn:
        rows = conn.execute("SELECT http_status FROM rejected_auth_callbacks").fetchall()
        assert all(row[0] == 401 for row in rows), "all rejected-auth rows MUST have http_status=401"

        # Direct INSERT with non-401 must be refused by the CHECK constraint.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO rejected_auth_callbacks "
                "(received_at, session_id, source_metadata_json, http_status) "
                "VALUES (?, ?, ?, ?)",
                ("2026-05-25T14:04:00Z", "sess-x", "{}", 500),
            )
            conn.commit()


# ----------------------------------------------------------------------------
# Assertion 6 — count_for_session matches JSONL line count
# ----------------------------------------------------------------------------


def test_count_for_session_matches_jsonl(
    rejected_auth_log: RejectedAuthCallbackLog,
    artifacts_root: Path,
) -> None:
    """``count_for_session(sid)`` returns the same count as the line count
    of ``artifacts/<sid>/rejected_auth_callbacks.jsonl``."""
    session_id = "sess-t013b-006"
    for i in range(3):
        rejected_auth_log.record(
            received_at=datetime(2026, 5, 25, 14, 5, i, tzinfo=timezone.utc),
            session_id=session_id,
            source_metadata={"attempt": str(i)},
        )

    expected = len(_read_jsonl(artifacts_root / session_id / "rejected_auth_callbacks.jsonl"))
    actual = rejected_auth_log.count_for_session(session_id)
    assert expected == actual == 3, f"jsonl_lines={expected} vs count_for_session={actual}"


# ----------------------------------------------------------------------------
# Assertion 7 — run_report surfaces rejected_auth_callbacks_count
# ----------------------------------------------------------------------------


def test_run_report_surfaces_count(
    rejected_auth_log: RejectedAuthCallbackLog,
    artifacts_root: Path,
    state_db_path: Path,
) -> None:
    """After N rejected-auth callbacks for a session, the run report shows
    ``rejected_auth_callbacks_count = N`` (FR-036).

    The run-report builder lands in T033; for T013b TDD red we assert against
    a hypothetical ``artifacts/<session_id>/run_report.json`` that T033 will
    produce. Until T033 lands, this test fails because the file does not
    exist — which is the right red signal."""
    session_id = "sess-t013b-007"
    for _ in range(2):
        rejected_auth_log.record(
            received_at=datetime(2026, 5, 25, 14, 6, 0, tzinfo=timezone.utc),
            session_id=session_id,
            source_metadata={},
        )

    run_report_path = artifacts_root / session_id / "run_report.json"
    assert run_report_path.exists(), (
        f"T033 must build {run_report_path} after the session finalizes; "
        "T013b asserts the rejected-auth count is surfaced there per FR-036"
    )
    report = json.loads(run_report_path.read_text(encoding="utf-8"))
    assert report.get("rejected_auth_callbacks_count") == 2, (
        f"run report must surface rejected_auth_callbacks_count=2, "
        f"got {report.get('rejected_auth_callbacks_count')}"
    )


# ----------------------------------------------------------------------------
# Assertion 8 — no SIGNALWIRE_SIGNING_SECRET substring across all files
# ----------------------------------------------------------------------------


def test_no_secrets_in_artifact_files(
    rejected_auth_log: RejectedAuthCallbackLog,
    artifacts_root: Path,
) -> None:
    """grep for any ``SIGNALWIRE_SIGNING_SECRET`` substring across every
    ``artifacts/**/rejected_auth_callbacks.jsonl`` file returns 0 matches
    (SC-018)."""
    # Drive a few rejections across multiple sessions.
    for i in range(3):
        rejected_auth_log.record(
            received_at=datetime(2026, 5, 25, 14, 7, i, tzinfo=timezone.utc),
            session_id=f"sess-t013b-008-{i}",
            source_metadata={"remote_addr": f"192.0.2.{i}"},
        )

    jsonl_files = list(artifacts_root.rglob("rejected_auth_callbacks.jsonl"))
    assert jsonl_files, "no rejected-auth JSONL files were produced"

    for path in jsonl_files:
        text = path.read_text(encoding="utf-8")
        assert SIGNALWIRE_SIGNING_SECRET_SENTINEL not in text, (
            f"SC-018 violation: signing-secret sentinel substring found in {path}"
        )
        # Also explicitly check the literal env-var name does not appear —
        # operators sometimes accidentally log `os.environ["FOO"]`-style
        # diagnostics.
        assert "SIGNALWIRE_SIGNING_SECRET" not in text, (
            f"SC-018 violation: literal env var name leaked into {path}"
        )
