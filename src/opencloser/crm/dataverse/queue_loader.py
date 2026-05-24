"""Dataverse queue intake — Slice 2 (FR-008-FR-011).

`DataverseQueueLoader` reads one ALF queue item from Dataverse and maps it into the
unchanged Slice 1 `QueueItem` contract consumed by the eligibility evaluator. It is
read-only — it never claims or mutates the queue row (the in-progress mark happens
later, per FR-010). See contracts/dataverse-queue-loader.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.errors import odata_string_literal
from opencloser.crm.dataverse.mapping import MappingError, MappingTranslator
from opencloser.models import CallableStatus, DataverseFieldRef, QueueBaseline, QueueItem

# The Dataverse system-field name that every table carries — used as the
# next-ready tie-breaker between two rows with the same next_attempt_at
# (FR-008, contracts/dataverse-queue-loader.md).
_DATAVERSE_CREATED_AT_FIELD = "createdon"

# Conceptual mapping keys this module references repeatedly — extracted so a typo
# fails once and the key is a single source of truth.
_QUEUE_STATUS_FIELD = "queue.status"


def _lookup_value_name(field_ref: DataverseFieldRef) -> str:
    """Dataverse exposes lookup column GUIDs in a *computed* property named
    `_<logical>_value` (with a leading underscore), not in the navigation property
    itself; the same name is also what `$filter` predicates must reference. For
    non-lookup fields the logical name IS the scalar property. (Codex review on PR #3.)
    """
    if field_ref.type == "lookup":
        return f"_{field_ref.logical_name}_value"
    return field_ref.logical_name


# Field types whose `$filter` RHS is a bare literal that goes through the strict
# token validator (GUID, integer). Booleans need their own special-case path
# because OData requires lowercase `true`/`false` (not Python's `True`/`False`).
# Everything else is treated as a quoted string ('value'). Adding more types here
# (e.g. `datetime`) is a deliberate decision — datetimes need their own RFC3339 form.
_BARE_LITERAL_TYPES = frozenset({"lookup", "integer"})


def _odata_value(field_type: str, value: object) -> str:
    """Render `value` as an OData `$filter` RHS appropriate for `field_type`.

    Booleans render as lowercase `true`/`false` (the OData literal form;
    Python's `str(True)` = `"True"` would be invalid OData — Copilot review on
    PR #3). Lookups (`_<name>_value` GUIDs) and integers go in bare and ARE
    routed through `_odata_token` — those types really shouldn't carry reserved
    characters and the strict validator catches typos and injection attempts.
    String values use the OData string-literal form: escape `'` → `''` and wrap
    in single quotes. Validation isn't needed for strings — the single-quote
    wrapping confines the value, and legitimate campaign names commonly contain
    spaces, periods, or apostrophes that the strict token validator would reject
    (Codex follow-up review on PR #3).
    """
    if field_type == "boolean":
        if isinstance(value, bool):
            return "true" if value else "false"
        text = str(value).lower()
        if text not in ("true", "false"):
            raise QueueLoadError(
                f"invalid OData boolean value {value!r} — expected true/false"
            )
        return text
    if field_type in _BARE_LITERAL_TYPES:
        return _odata_token(value)
    return odata_string_literal(str(value))

# Dataverse expects record/lookup ids unquoted in `$filter` (GUIDs); we accept any
# value matching this safe alphanumeric+dash+underscore pattern (which covers real
# GUIDs and the test fixture ids) and reject anything containing OData reserved or
# whitespace characters so a malformed/hostile value cannot break the filter or
# inject extra clauses.
_SAFE_ODATA_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")


def _odata_token(value: object) -> str:
    """Return `value` if it is a safe unquoted OData filter token (alphanumeric +
    `_` / `-`), else raise. Used for record-id and lookup-id values that Dataverse
    expects unquoted; reserved characters (`'`, ` `, `,`, `)`, ...) would corrupt
    the `$filter` or enable injection."""
    text = str(value)
    if not _SAFE_ODATA_TOKEN.fullmatch(text):
        raise QueueLoadError(
            f"unsafe OData filter value {value!r} — must match [A-Za-z0-9_-]+"
        )
    return text


class QueueLoadError(RuntimeError):
    """Raised when a Dataverse queue row cannot be mapped to the `QueueItem` contract."""


class CampaignNotFoundError(QueueLoadError):
    """T051 — raised when a ``NextReady`` selector's configured campaign has ZERO
    queue items in Dataverse (callable OR not). Distinguishes the spec §Edge Cases
    "Configured campaign not found" path from FR-009's "Empty queue" clean no-op:

      * **Empty queue (FR-009)**: at least one queue row exists for the campaign,
        but none are in the configured callable status — clean ``no-callable-item``
        no-op.
      * **Campaign not found (this exception)**: zero queue rows exist for the
        campaign at all, meaning the configured campaign selector likely doesn't
        resolve in Dataverse (typo, deleted campaign, wrong environment) — fails
        as a permanent configuration/readiness error per spec §Edge Cases.

    The runner converts this to ``CrmRunReport(exit_status="failed", message=
    "configured_campaign_not_found: ...")`` per spec §Edge Cases ("fails as a
    permanent configuration/readiness error before session creation, queue claim,
    mock call placement, attempt increment, or CRM write").

    Note: a campaign that genuinely has zero queue items (e.g. a brand-new
    campaign before any items are queued) is indistinguishable here from a
    typo'd campaign GUID — both have zero rows. The trade-off favors the
    typo case because (a) it's the dominant operator-error scenario and (b)
    a campaign with literal zero items has no work to do regardless of
    exit-status label.
    """

    def __init__(self, campaign: str) -> None:
        self.campaign = campaign
        super().__init__(
            f"configured_campaign_not_found: campaign {campaign!r} has zero queue items in "
            "Dataverse (typo'd selector, deleted campaign, or wrong environment); spec §Edge "
            "Cases requires this to fail as a permanent configuration/readiness error, "
            "distinct from FR-009 empty-queue no-op (which requires at least one queue "
            "item to exist for the campaign)."
        )


@dataclass(frozen=True)
class ExplicitId:
    """Selector — load one specific Dataverse queue item by its primary id."""

    queue_item_id: str


@dataclass(frozen=True)
class NextReady:
    """Selector — load the deterministically-next callable queue item for a campaign."""

    campaign: str


QueueSelector = ExplicitId | NextReady


class DataverseQueueLoader:
    """Loads one ALF queue item from Dataverse into the Slice 1 `QueueItem` contract."""

    def __init__(
        self,
        client: DataverseClient,
        translator: MappingTranslator,
        *,
        callable_status: str = "ready",
    ) -> None:
        self._client = client
        self._t = translator
        # The configured callable status (FR-011 / config/slice2.toml [dataverse]
        # callable_status). The conceptual option-set key is `queue_status.<name>`.
        self._callable_status = callable_status

    def load(self, selector: QueueSelector) -> QueueItem | None:
        """Return the selected queue item mapped to `QueueItem`, or None for an empty
        queue (FR-009). Read-only — never claims or mutates the row.

        With an `ExplicitId` selector, a row not in the configured callable status is
        still returned (mapped to its conceptual status) so the reused eligibility
        evaluator records the FR-011 blocked result — filtering it out here would hide
        that decision. The `NextReady` selector, by contrast, filters on the configured
        callable status in the Dataverse query itself (so a non-callable row is never
        a "next ready" candidate).
        """
        row = self._fetch_one_row(selector)
        if row is None:
            return None
        return self._to_queue_item(row, self._primary_id_or_default())

    def load_with_baseline(
        self, selector: QueueSelector, *, now_utc_ms: str
    ) -> tuple[QueueItem, QueueBaseline] | None:
        """T045 — like ``load`` but also returns a ``QueueBaseline`` snapshot
        of the row's status + ``preserve_if_present`` field values at load
        time. The adapter's ``_check_conflict`` compares this baseline against
        a fresh GET immediately before the final queue-status PATCH; any
        mismatch raises ``CrmConflictError`` and the runner surfaces
        ``exit_status="blocked"``.

        The baseline is captured from the same row that produces the
        ``QueueItem`` — single GET, consistent snapshot, no extra Dataverse
        round-trip at startup.
        """
        row = self._fetch_one_row(selector)
        if row is None:
            return None
        primary_id = self._primary_id_or_default()
        queue_item = self._to_queue_item(row, primary_id)
        baseline = self._baseline_from_row(row, queue_item.queue_item_id, now_utc_ms)
        return queue_item, baseline

    def _primary_id_or_default(self) -> str:
        entity_logical = self._t.entity_logical_name("queue_item")
        return self._t.entity("queue_item").primary_id or f"{entity_logical}id"

    def _fetch_one_row(self, selector: QueueSelector) -> dict | None:
        """Run the selector's Dataverse query and return the raw row dict, or
        None for an empty result. Shared by ``load`` and ``load_with_baseline``
        so the (somewhat involved) selector → $filter translation lives in
        exactly one place."""
        # Record CRUD URLs use the entity-set name (often plural); only metadata uses
        # the singular logical name (Copilot PR #3 review).
        entity_set = self._t.entity_set_name("queue_item")
        primary_id = self._primary_id_or_default()

        if isinstance(selector, ExplicitId):
            rows = self._query(
                entity_set,
                flt=f"{primary_id} eq {_odata_token(selector.queue_item_id)}",
                top=1,
            )
        else:
            status_field = self._t.logical_name(_QUEUE_STATUS_FIELD)
            callable_value = self._t.option_set_value(f"queue_status.{self._callable_status}")
            order_field = self._t.logical_name("queue.next_attempt_at")
            filter_clauses = [f"{status_field} eq {callable_value}"]
            # FR-009 single-campaign scoping: filter on the mapped campaign field when
            # the deployment maps one. A mapping without `queue.campaign` is treated as
            # a single-campaign queue table where this filter is unnecessary. When the
            # mapped campaign field is a Dataverse lookup, the filter LHS MUST be the
            # `_<logical>_value` computed property; the RHS quoting depends on the field
            # type — GUID/int/bool are bare, strings are `'value'` (Codex review on PR #3).
            campaign_field_ref = self._optional_field("queue.campaign")
            if campaign_field_ref is not None:
                if not selector.campaign:
                    # An empty/whitespace campaign with a mapped campaign field would
                    # silently widen the query across all campaigns — almost always an
                    # operator error. Fail explicitly so the cross-campaign read can't
                    # happen by accident (Codex review on PR #3).
                    raise QueueLoadError(
                        "NextReady requires a non-empty campaign selector when the "
                        "mapping defines `queue.campaign`"
                    )
                filter_clauses.append(
                    f"{_lookup_value_name(campaign_field_ref)} eq "
                    f"{_odata_value(campaign_field_ref.type, selector.campaign)}"
                )
            else:
                raise QueueLoadError(
                    "NextReady requires `queue.campaign` in the Dataverse mapping "
                    "so the query cannot widen across campaigns"
                )
            rows = self._query(
                entity_set,
                flt=" and ".join(filter_clauses),
                # FR-008 deterministic next-ready ordering: earliest next_attempt_at,
                # then oldest CRM-created (`createdon`), then stable primary id.
                orderby=(
                    f"{order_field} asc,"
                    f"{_DATAVERSE_CREATED_AT_FIELD} asc,"
                    f"{primary_id} asc"
                ),
                top=1,
            )
            if not rows:
                # T051 — disambiguate FR-009 empty-queue from spec §Edge Cases
                # "Configured campaign not found". The status+campaign filter
                # returned 0 rows; re-query with ONLY the campaign filter (drop
                # the status). If still 0 → the campaign has no queue items at
                # all (typo'd selector, deleted campaign, or wrong environment)
                # — raise `CampaignNotFoundError` so the runner can surface a
                # permanent configuration/readiness error per spec §Edge Cases.
                # If ≥1 → at least one queue item exists for the campaign but
                # none are callable → real FR-009 empty-queue no-op; fall
                # through to `return None`.
                campaign_only_rows = self._query(
                    entity_set,
                    flt=(
                        f"{_lookup_value_name(campaign_field_ref)} eq "
                        f"{_odata_value(campaign_field_ref.type, selector.campaign)}"
                    ),
                    top=1,
                )
                if not campaign_only_rows:
                    raise CampaignNotFoundError(selector.campaign)
        return rows[0] if rows else None

    def _baseline_from_row(
        self, row: dict, queue_item_id: str, captured_at: str
    ) -> QueueBaseline:
        """Extract the T045 conflict-detection baseline from a Dataverse row:
        the current ``queue.status`` option-set integer plus the current value
        of every ``preserve_if_present`` logical name. Missing fields surface
        as ``None`` so the adapter's ``_check_conflict`` can detect a
        human-added value (None → non-None) the same way it detects edits."""
        status_field = self._t.logical_name(_QUEUE_STATUS_FIELD)
        return QueueBaseline(
            queue_item_id=queue_item_id,
            captured_at=captured_at,
            status_value=int(row.get(status_field, 0) or 0),
            preserve_values={
                logical: row.get(logical)
                for logical in self._t.preserve_if_present()
            },
        )

    def _optional_logical_name(self, conceptual: str) -> str | None:
        """The Dataverse logical name for a conceptual field, or None when the mapping
        does not include it (callers fall back to default behavior)."""
        try:
            return self._t.logical_name(conceptual)
        except MappingError:
            return None

    def _optional_field(self, conceptual: str) -> DataverseFieldRef | None:
        """The full field-ref for a conceptual field, or None when the mapping omits
        it. Callers that need the field's `type` (e.g. for lookup-property handling)
        use this rather than `_optional_logical_name`."""
        try:
            return self._t.field(conceptual)
        except MappingError:
            return None

    def _query(
        self,
        entity: str,
        *,
        flt: str,
        top: int | None = None,
        orderby: str | None = None,
    ) -> list[dict]:
        params: dict[str, str] = {"$filter": flt}
        if orderby is not None:
            params["$orderby"] = orderby
        if top is not None:
            params["$top"] = str(top)
        return self._client.get(entity, params=params).json().get("value", [])

    def _to_queue_item(self, row: dict, primary_id: str) -> QueueItem:
        status_logical = self._t.logical_name(_QUEUE_STATUS_FIELD)
        raw_status = row.get(status_logical)
        status_key = self._t.option_set_key_for_value(_QUEUE_STATUS_FIELD, raw_status)
        if status_key is None:
            raise QueueLoadError(
                f"queue item {row.get(primary_id)!r} carries an unmapped "
                f"{status_logical}={raw_status!r} option-set value"
            )
        callable_status = CallableStatus(status_key.split(".", 1)[1])
        attempt_count = row.get(self._t.logical_name("queue.attempt_count")) or 0
        return QueueItem(
            queue_item_id=str(row[primary_id]),
            facility_name=self._facility_name(row),
            phone_number=row.get(self._t.logical_name("queue.phone")),
            timezone=row.get(self._t.logical_name("queue.timezone")),
            attempt_count=int(attempt_count),
            dnc_flag=bool(row.get(self._t.logical_name("queue.dnc"))),
            callable_status=callable_status,
        )

    def _facility_name(self, row: dict) -> str:
        """Resolve the facility name from the Account lookup; fall back to the raw id
        or empty string when the lookup is absent."""
        try:
            account_field = self._t.field("queue.facility_account")
        except MappingError:
            # A deployment without an Account lookup mapping is accepted — the
            # facility_name simply defaults to empty rather than raising.
            return ""
        # Lookup column GUIDs come back in the `_<logical>_value` computed property
        # in real Dataverse, not under the bare logical name (Codex review on PR #3).
        account_id = row.get(_lookup_value_name(account_field))
        if not account_id:
            return ""
        # `lookup_target` is the conceptual entity key. Prefer the mapped entity's
        # entity-set name (and its primary id); fall back to the raw key string if no
        # entry exists (single-source compatibility for minimal scaffold mappings).
        account_entity_key = account_field.lookup_target or "account"
        try:
            account_ref = self._t.entity(account_entity_key)
            account_set = account_ref.entity_set_name or account_ref.logical_name
            account_primary_id = (
                account_ref.primary_id or f"{account_ref.logical_name}id"
            )
        except MappingError:
            account_set = account_entity_key
            account_primary_id = f"{account_entity_key}id"
        accounts = (
            self._client.get(
                account_set,
                params={
                    "$filter": f"{account_primary_id} eq {_odata_token(account_id)}",
                    "$select": "name",
                    "$top": "1",
                },
            )
            .json()
            .get("value", [])
        )
        if accounts and accounts[0].get("name"):
            return str(accounts[0]["name"])
        return str(account_id)
