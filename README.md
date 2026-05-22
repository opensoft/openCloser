# openCloser

A CRM-first AI communication platform for healthcare-oriented outreach.

## Active feature

**Slice 1 — Mock Call, Mock CRM**

The first end-to-end product loop on a single ALF prospect queue record, fixture-driven, with no real telephony, no real CRM, no UI. Proves the five module boundaries (Interaction Core, Eligibility, Mock Call Transport, Persona, Mock CRM Write-back) before swapping in real SignalWire (Slice 2) and Dataverse (Slice 2+).

See:

- [Specification](specs/001-mock-call-mock-crm/spec.md) — what is built and why
- [Plan](specs/001-mock-call-mock-crm/plan.md) — technical decisions and project structure
- [Tasks](specs/001-mock-call-mock-crm/tasks.md) — ordered task list for implementation
- [Quickstart](specs/001-mock-call-mock-crm/quickstart.md) — install, run, and inspect artifacts in 8 steps
- [Constitution](.specify/memory/constitution.md) — binding project principles

## Status

Slice 1 is complete — spec, plan, tasks, contracts, checklists, and the end-to-end implementation (all 75 tasks in `tasks.md`). Run the Bootstrap steps below to exercise the mock loop.

## Bootstrap (developers)

```bash
uv sync
uv run opencloser init-state
uv run opencloser load-queue-item --file tests/fixtures/queue_items/alf-prospect-001.json
uv run opencloser run-one --queue-item-id alf-prospect-001 \
    --conversation-fixture tests/fixtures/conversations/interested_callback_requested.json \
    --transport-fixture tests/fixtures/transport_events/connected.json
```

See [`quickstart.md`](specs/001-mock-call-mock-crm/quickstart.md) for the full walkthrough.
