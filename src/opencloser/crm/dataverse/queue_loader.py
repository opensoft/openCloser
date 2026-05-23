"""Dataverse queue intake — Slice 2 (FR-008-FR-011).

`DataverseQueueLoader` reads one ALF queue item from Dataverse and maps it into the
unchanged Slice 1 `QueueItem` contract consumed by the eligibility evaluator. It is
read-only — it never claims or mutates the queue row (the in-progress mark happens
later, per FR-010). See contracts/dataverse-queue-loader.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.mapping import MappingError, MappingTranslator
from opencloser.models import CallableStatus, QueueItem

# The Dataverse system-field name that every table carries — used as the
# next-ready tie-breaker between two rows with the same next_attempt_at
# (FR-008, contracts/dataverse-queue-loader.md).
_DATAVERSE_CREATED_AT_FIELD = "createdon"


class QueueLoadError(RuntimeError):
    """Raised when a Dataverse queue row cannot be mapped to the `QueueItem` contract."""


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

        A row not in the configured callable status is still returned (mapped to its
        conceptual status) so the reused eligibility evaluator records the FR-011
        blocked result — filtering it out here would hide that decision.
        """
        entity = self._t.entity_logical_name("queue_item")
        primary_id = self._t.mapping.entities["queue_item"].primary_id or f"{entity}id"

        if isinstance(selector, ExplicitId):
            rows = self._query(entity, flt=f"{primary_id} eq {selector.queue_item_id}", top=1)
        else:
            status_field = self._t.logical_name("queue.status")
            callable_value = self._t.option_set_value(f"queue_status.{self._callable_status}")
            order_field = self._t.logical_name("queue.next_attempt_at")
            filter_clauses = [f"{status_field} eq {callable_value}"]
            # FR-009 single-campaign scoping: filter on the mapped campaign field when
            # the deployment maps one. A mapping without `queue.campaign` is treated as
            # a single-campaign queue table where this filter is unnecessary.
            campaign_field = self._optional_logical_name("queue.campaign")
            if campaign_field and selector.campaign:
                filter_clauses.append(f"{campaign_field} eq {selector.campaign}")
            rows = self._query(
                entity,
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
            return None
        return self._to_queue_item(rows[0], primary_id)

    def _optional_logical_name(self, conceptual: str) -> str | None:
        """The Dataverse logical name for a conceptual field, or None when the mapping
        does not include it (callers fall back to default behavior)."""
        try:
            return self._t.logical_name(conceptual)
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
        status_logical = self._t.logical_name("queue.status")
        raw_status = row.get(status_logical)
        status_key = self._t.option_set_key_for_value("queue.status", raw_status)
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
        """Resolve the facility name from the Account lookup; fall back to the raw id."""
        account_field = self._t.field("queue.facility_account")
        account_id = row.get(account_field.logical_name)
        if not account_id:
            return ""
        account_entity = account_field.lookup_target or "account"
        accounts = (
            self._client.get(
                account_entity,
                params={
                    "$filter": f"accountid eq {account_id}",
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
