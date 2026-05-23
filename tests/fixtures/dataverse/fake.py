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
_PICKLIST_RE = re.compile(
    r"^EntityDefinitions\(LogicalName='([^']+)'\)"
    r"/Attributes\(LogicalName='([^']+)'\)"
    r"/Microsoft\.Dynamics\.CRM\.PicklistAttributeMetadata$"
)
_RECORD_RE = re.compile(r"^(\w+)\(([^)]+)\)$")


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
        env_url: str = "https://fake.crm.dynamics.com",
    ) -> None:
        self.env_url = env_url
        self._entities = {name: set(attrs) for name, attrs in entities.items()}
        self._records = {name: [dict(r) for r in recs] for name, recs in (records or {}).items()}
        # (entity_logical, attribute_logical) -> set of valid option-set integer values
        self._option_sets = {k: set(v) for k, v in (option_sets or {}).items()}
        self._fail_remaining = 0
        self._fail_status = 503
        self.created: list[tuple[str, dict[str, Any]]] = []  # (entity, record) — POST log
        self.patched: list[tuple[str, str, dict[str, Any]]] = []  # (entity, id, changes)
        self.request_count = 0

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

        picklist = _PICKLIST_RE.match(resource)
        if picklist is not None and method == "GET":
            return self._handle_picklist_metadata(request, picklist.group(1), picklist.group(2))

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
        return httpx.Response(200, json={"LogicalName": logical_name}, request=request)

    def _handle_picklist_metadata(
        self, request: httpx.Request, entity_logical: str, attr_logical: str
    ) -> httpx.Response:
        """Serve the OptionSet for an attribute (or 404 when the entity/attribute is
        unknown or no option_set was registered for it)."""
        if (
            entity_logical not in self._entities
            or attr_logical not in self._entities[entity_logical]
        ):
            return httpx.Response(404, request=request)
        values = self._option_sets.get((entity_logical, attr_logical))
        if values is None:
            return httpx.Response(404, request=request)
        options = [{"Value": v} for v in sorted(values)]
        return httpx.Response(
            200, json={"OptionSet": {"Options": options}}, request=request
        )

    def _handle_query(self, request: httpx.Request, entity: str) -> httpx.Response:
        if entity not in self._entities:
            return httpx.Response(404, request=request)
        rows = list(self._records.get(entity, []))
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
            unknown = [k for k in keys if k not in self._entities[entity]]
            if unknown:  # a $select of an unmapped field is a Dataverse 400
                return httpx.Response(
                    400, json={"error": {"message": f"unknown field(s): {unknown}"}},
                    request=request,
                )
            rows = [{k: r.get(k) for k in keys} for r in rows]
        return httpx.Response(200, json={"value": rows}, request=request)

    def _handle_create(self, request: httpx.Request, entity: str) -> httpx.Response:
        if entity not in self._entities:
            return httpx.Response(404, request=request)
        body = json.loads(request.content or b"{}")
        record_id = str(uuid.uuid4())
        body.setdefault(f"{entity}id", record_id)
        self._records.setdefault(entity, []).append(dict(body))
        self.created.append((entity, dict(body)))
        entity_uri = f"{self.env_url}{_API_PREFIX}{entity}({record_id})"
        return httpx.Response(204, headers={"OData-EntityId": entity_uri}, request=request)

    def _handle_patch(self, request: httpx.Request, entity: str, record_id: str) -> httpx.Response:
        if entity not in self._entities:
            return httpx.Response(404, request=request)
        changes = json.loads(request.content or b"{}")
        rid = record_id.strip("'")
        for row in self._records.get(entity, []):
            if row.get(f"{entity}id") == rid:
                row.update(changes)
                self.patched.append((entity, rid, dict(changes)))
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
            expected: Any = raw[1:-1]
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
