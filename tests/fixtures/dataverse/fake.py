"""In-process Dataverse Web API fake — Slice 2 test double (task T015, research.md §10).

A small, deterministic stand-in for the Dataverse Web API (OData v4) backed by
in-memory state: entity/attribute metadata, record query (GET), create (POST), and
update (PATCH), plus injectable transient/permanent failures. Integration tests run
against this fake so CI never touches a live Dataverse environment.

This models the subset of the Web API that Slice 2 exercises. The exact entity-set
URL naming and metadata-payload shape of a real environment are confirmed by
`opencloser discover-crm` against live Dataverse; here both client and fake key on a
single entity name for determinism.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterable
from typing import Any

import httpx

from opencloser.crm.dataverse.client import DataverseClient
from opencloser.models import RetryConfig

_API_PREFIX = "/api/data/v9.2/"
_ENTITY_DEF_RE = re.compile(r"^EntityDefinitions\(LogicalName='([^']+)'\)(/Attributes)?$")
# Match Picklist OR Status metadata casts — Dataverse exposes option-set columns
# under several derived types and the loader/verifier tries them in order.
_OPTION_SET_META_RE = re.compile(
    r"^EntityDefinitions\(LogicalName='([^']+)'\)"
    r"/Attributes\(LogicalName='([^']+)'\)"
    r"/Microsoft\.Dynamics\.CRM\.(Picklist|Status)AttributeMetadata$"
)
_RECORD_RE = re.compile(r"^(\w+)\(([^)]+)\)$")
_ACTIVITY_LOGICAL_NAMES = frozenset({"phonecall", "task", "email", "appointment"})


class _StubToken:
    """A token provider stub — the fake does not authenticate."""

    def token(self) -> str:
        return "fake-token"


class DataverseFake:
    """An in-memory Dataverse Web API fake usable as an httpx transport.

    `entities` maps an entity name to its set of valid attribute logical names;
    `records` maps an entity name to a list of record dicts.
    """

    def __init__(
        self,
        *,
        entities: dict[str, Iterable[str]],
        records: dict[str, list[dict[str, Any]]] | None = None,
        option_sets: dict[tuple[str, str], Iterable[int]] | None = None,
        status_option_sets: dict[tuple[str, str], Iterable[int]] | None = None,
        global_option_sets: dict[tuple[str, str], Iterable[int]] | None = None,
        entity_sets: dict[str, str] | None = None,
        env_url: str = "https://fake.crm.dynamics.com",
    ) -> None:
        self.env_url = env_url
        self._entities = {name: set(attrs) for name, attrs in entities.items()}
        self._records = {name: [dict(r) for r in recs] for name, recs in (records or {}).items()}
        # (entity_logical, attribute_logical) -> set of valid option-set integer values,
        # keyed by metadata cast ('Picklist' or 'Status'). The loader/verifier tries
        # casts in order and accepts the first hit (Codex review on PR #3).
        self._option_sets_by_cast: dict[str, dict[tuple[str, str], set[int]]] = {
            "Picklist": {k: set(v) for k, v in (option_sets or {}).items()},
            "Status": {k: set(v) for k, v in (status_option_sets or {}).items()},
        }
        # Global-choice option-sets: values come back under `GlobalOptionSet`
        # instead of `OptionSet` (Codex review on PR #3).
        self._global_option_sets: dict[tuple[str, str], set[int]] = {
            k: set(v) for k, v in (global_option_sets or {}).items()
        }
        # logical → entity-set name, for serving `EntitySetName` in entity-def
        # metadata responses (Codex review on PR #3).
        self._entity_set_names: dict[str, str] = dict(entity_sets or {})
        # Record-URL collection-name → internal logical key. Real Dataverse uses the
        # entity-set name (e.g. `accounts`) for record CRUD URLs but the logical name
        # for metadata URLs; the fake accepts EITHER as a record-URL collection so
        # legacy tests (logical-only) keep working alongside set-name-driven tests
        # (Copilot PR #3 review on `queue_loader.py`).
        self._collection_to_logical: dict[str, str] = {name: name for name in self._entities}
        for logical, set_name in (entity_sets or {}).items():
            self._collection_to_logical[set_name] = logical
        self._fail_remaining = 0
        self._fail_status = 503
        self.created: list[tuple[str, dict[str, Any]]] = []  # (entity, record) — POST log
        self.patched: list[tuple[str, str, dict[str, Any]]] = []  # (entity, id, changes)
        # ETag versioning per record (Pass 1B audit-remediation). Real
        # Dataverse returns `@odata.etag` on every GET and rejects mismatched
        # `If-Match` PATCHes with HTTP 412 Precondition Failed. The fake
        # emits a monotonic per-record version and bumps it on every PATCH.
        self._row_versions: dict[tuple[str, str], int] = {}
        self.request_count = 0

    def _resolve_collection(self, url_name: str) -> str | None:
        """URL record-collection name → internal logical key, or None if unknown."""
        return self._collection_to_logical.get(url_name)

    # -- failure injection -------------------------------------------------

    def fail_next(self, count: int, *, status: int = 503) -> None:
        """Make the next `count` requests fail with `status` (default 503 transient)."""
        self._fail_remaining = count
        self._fail_status = status

    # -- wiring ------------------------------------------------------------

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def client(self, retry: RetryConfig) -> DataverseClient:
        """A DataverseClient wired to this fake (no real network, no real auth)."""
        return DataverseClient(
            self.env_url,
            _StubToken(),
            retry,
            http=httpx.Client(transport=self.transport()),
            sleep=lambda _seconds: None,  # tests must not actually sleep
        )

    # -- request handling --------------------------------------------------

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.request_count += 1
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            return httpx.Response(self._fail_status, request=request)

        path = request.url.path
        if not path.startswith(_API_PREFIX):
            return httpx.Response(404, request=request)
        resource = path[len(_API_PREFIX) :]
        method = request.method.upper()

        option_set_meta = _OPTION_SET_META_RE.match(resource)
        if option_set_meta is not None and method == "GET":
            return self._handle_option_set_metadata(
                request,
                option_set_meta.group(1),
                option_set_meta.group(2),
                option_set_meta.group(3),  # 'Picklist' or 'Status'
            )

        meta = _ENTITY_DEF_RE.match(resource)
        if meta is not None:
            return self._handle_metadata(request, meta.group(1), bool(meta.group(2)))

        record = _RECORD_RE.match(resource)
        if record is not None and method == "PATCH":
            return self._handle_patch(request, record.group(1), record.group(2))

        if method == "GET":
            return self._handle_query(request, resource)
        if method == "POST":
            return self._handle_create(request, resource)
        return httpx.Response(405, request=request)

    def _handle_metadata(
        self, request: httpx.Request, logical_name: str, attributes: bool
    ) -> httpx.Response:
        if logical_name not in self._entities:
            return httpx.Response(404, request=request)
        if attributes:
            value = [{"LogicalName": attr} for attr in sorted(self._entities[logical_name])]
            return httpx.Response(200, json={"value": value}, request=request)
        # The entity-definition payload carries `EntitySetName` in real Dataverse;
        # surface what's registered in `entity_sets` (or fall back to the logical
        # name) so verification can compare against the mapping (Codex PR #3 review).
        body = {
            "LogicalName": logical_name,
            "EntitySetName": self._entity_set_names.get(logical_name, logical_name),
        }
        return httpx.Response(200, json=body, request=request)

    def _handle_option_set_metadata(
        self, request: httpx.Request, entity_logical: str, attr_logical: str, cast: str
    ) -> httpx.Response:
        """Serve the OptionSet for an attribute under the requested metadata cast
        ('Picklist' or 'Status'). Returns 404 when the entity/attribute is unknown
        OR when no option-set was registered for this cast (Codex review on PR #3).

        Values registered in `option_sets`/`status_option_sets` come back under
        `OptionSet`; values registered in `global_option_sets` come back under
        `GlobalOptionSet` with `OptionSet` null — mirroring how Dataverse exposes
        local vs. referenced-global choices.
        """
        if (
            entity_logical not in self._entities
            or attr_logical not in self._entities[entity_logical]
        ):
            return httpx.Response(404, request=request)
        values = self._option_sets_by_cast[cast].get((entity_logical, attr_logical))
        if values is not None:
            options = [{"Value": v} for v in sorted(values)]
            return httpx.Response(
                200, json={"OptionSet": {"Options": options}}, request=request
            )
        global_values = self._global_option_sets.get((entity_logical, attr_logical))
        if global_values is not None:
            options = [{"Value": v} for v in sorted(global_values)]
            return httpx.Response(
                200,
                json={
                    "OptionSet": None,
                    "GlobalOptionSet": {"Options": options},
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    def _handle_query(self, request: httpx.Request, entity: str) -> httpx.Response:
        logical = self._resolve_collection(entity)
        if logical is None:
            return httpx.Response(404, request=request)
        rows = list(self._records.get(logical, []))
        params = request.url.params

        flt = params.get("$filter")
        if flt:
            rows = [r for r in rows if _matches_filter(r, flt)]
        orderby = params.get("$orderby")
        if orderby:
            rows = _apply_orderby(rows, orderby)
        top = params.get("$top")
        if top:
            rows = rows[: int(top)]
        select = params.get("$select")
        if select:
            keys = [k.strip() for k in select.split(",")]
            unknown = [k for k in keys if k not in self._entities[logical]]
            if unknown:  # a $select of an unmapped field is a Dataverse 400
                return httpx.Response(
                    400, json={"error": {"message": f"unknown field(s): {unknown}"}},
                    request=request,
                )
            projected = [{k: r.get(k) for k in keys} for r in rows]
            rows = projected
        # Pass 1B audit-remediation: inject `@odata.etag` per row so callers
        # (specifically `QueueLoader._baseline_from_row`) can capture the
        # optimistic-concurrency token. Real Dataverse emits this annotation
        # when `Prefer: odata.include-annotations=*` is set; the fake emits
        # it unconditionally so tests can opt into ETag-aware flows.
        annotated: list[dict[str, Any]] = []
        primary_id_field = f"{logical}id"
        for row in rows:
            # Find a usable record id — if $select stripped it, fall back to
            # whatever the unprojected record stored. (Activities can carry
            # `activityid` instead of `<logical>id`.)
            rid = row.get(primary_id_field) or row.get("activityid")
            if rid is None:
                # Unprojected fields lookup — find the source row.
                for source in self._records.get(logical, []):
                    if all(source.get(k) == v for k, v in row.items() if v is not None):
                        rid = source.get(primary_id_field) or source.get("activityid")
                        break
            annotated_row = dict(row)
            if rid is not None:
                version = self._row_versions.setdefault((logical, str(rid)), 1)
                annotated_row["@odata.etag"] = f'W/"{version}"'
            annotated.append(annotated_row)
        return httpx.Response(200, json={"value": annotated}, request=request)

    def _handle_create(self, request: httpx.Request, entity: str) -> httpx.Response:
        logical = self._resolve_collection(entity)
        if logical is None:
            return httpx.Response(404, request=request)
        body = json.loads(request.content or b"{}")
        record_id = str(uuid.uuid4())
        body.setdefault(f"{logical}id", record_id)
        if logical in _ACTIVITY_LOGICAL_NAMES:
            body.setdefault("activityid", record_id)
        self._records.setdefault(logical, []).append(dict(body))
        self.created.append((logical, dict(body)))
        entity_uri = f"{self.env_url}{_API_PREFIX}{entity}({record_id})"
        return httpx.Response(204, headers={"OData-EntityId": entity_uri}, request=request)

    def _handle_patch(self, request: httpx.Request, entity: str, record_id: str) -> httpx.Response:
        logical = self._resolve_collection(entity)
        if logical is None:
            return httpx.Response(404, request=request)
        changes = json.loads(request.content or b"{}")
        rid = record_id.strip("'")
        for row in self._records.get(logical, []):
            if row.get(f"{logical}id") == rid or (
                logical in _ACTIVITY_LOGICAL_NAMES and row.get("activityid") == rid
            ):
                # Pass 1B audit-remediation: honor `If-Match: <etag>` for
                # optimistic-concurrency PATCHes. Real Dataverse returns
                # HTTP 412 Precondition Failed when the supplied etag
                # doesn't match the current row version.
                if_match = request.headers.get("If-Match")
                if if_match is not None:
                    current_version = self._row_versions.setdefault((logical, rid), 1)
                    if if_match != f'W/"{current_version}"':
                        return httpx.Response(412, request=request)
                row.update(changes)
                # Bump the row version so a subsequent PATCH with the old
                # etag would 412.
                self._row_versions[(logical, rid)] = (
                    self._row_versions.get((logical, rid), 1) + 1
                )
                self.patched.append((logical, rid, dict(changes)))
                return httpx.Response(204, request=request)
        return httpx.Response(404, request=request)


def _matches_filter(row: dict[str, Any], flt: str) -> bool:
    """Support the minimal OData `$filter` Slice 2 uses: `field eq value` (string,
    int, or guid), optionally joined by ` and `.

    Implemented with plain string splitting (no regex) — Sonar flagged a previous
    regex variant for polynomial-backtracking ReDoS risk (rule python:S5852).
    """
    for raw_clause in flt.split(" and "):
        clause = raw_clause.strip()
        if " eq " not in clause:
            return False
        field, raw = (part.strip() for part in clause.split(" eq ", 1))
        if not field or not field.replace("_", "").isalnum():
            return False
        if raw.startswith("'") and raw.endswith("'"):
            # OData string literals escape `'` as `''` — unescape on the way out
            # so the comparison value matches what the seeded row stores.
            expected: Any = raw[1:-1].replace("''", "'")
        elif raw.lower() in ("true", "false"):
            expected = raw.lower() == "true"
        else:
            expected = int(raw) if raw.lstrip("-").isdigit() else raw
        if row.get(field) != expected:
            return False
    return True


def _apply_orderby(rows: list[dict[str, Any]], orderby: str) -> list[dict[str, Any]]:
    """Deterministic multi-key `$orderby` (`field [asc|desc], ...`)."""
    ordered = list(rows)
    for term in reversed([t.strip() for t in orderby.split(",")]):
        parts = term.split()
        field = parts[0]
        descending = len(parts) > 1 and parts[1].lower() == "desc"
        ordered.sort(key=lambda r, f=field: (r.get(f) is None, r.get(f)), reverse=descending)
    return ordered
