<!--
Sync Impact Report
Version change: N/A -> 1.0.0
Modified principles:
- Template Principle 1 -> I. CRM Is the Control Plane
- Template Principle 2 -> II. Thin Slices Before Platform Surface
- Template Principle 3 -> III. Core, Adapters, and Personas Stay Separate
- Template Principle 4 -> IV. Automation Is Auditable and Idempotent
- Template Principle 5 -> V. Safety, Privacy, and Human Handoff Are Required Paths
Added sections:
- Architecture Constraints
- Delivery Workflow
Removed sections:
- Placeholder Section 2
- Placeholder Section 3
Templates requiring updates:
- .specify/templates/plan-template.md - updated
- .specify/templates/spec-template.md - updated
- .specify/templates/tasks-template.md - updated
- .specify/templates/checklist-template.md - updated
- .specify/templates/commands/*.md - not present
Runtime guidance requiring updates:
- AGENTS.md - updated
- CLAUDE.md - updated
- GEMINI.md - updated
- KIMI.md - updated
- QWEN.md - updated
- .github/copilot-instructions.md - updated
Follow-up TODOs:
- None
-->

# openCloser Constitution

## Core Principles

### I. CRM Is the Control Plane
openCloser MUST treat CRM as the operational source of truth for outreach
workflow, business records, and human follow-up. MVP and pilot features MUST
read from CRM-owned queue or account context when real CRM is in scope and MUST
write structured outcomes back as CRM activities, tasks, queue updates, or
durable field updates. The product MUST NOT introduce a parallel campaign UI,
custom task queue, or replacement CRM unless a later constitution amendment and
product spec explicitly allow it.

Rationale: Operators already live in Dynamics/Sales Hub. The product wins by
making that workflow auditable and faster, not by creating another system to
manage.

### II. Thin Slices Before Platform Surface
Every feature MUST be deliverable as a narrow, independently demonstrable slice.
The current MVP order is binding until amended:

1. Mock call, mock CRM.
2. Mock call, real CRM.
3. Real call, real CRM.

Plans MUST name the target slice and MUST reject broad platform work that does
not directly advance the queue, eligibility, call, persona, result, write-back,
or human-follow-up loop. Custom UI, multi-provider support, generalized workflow
engines, distributed job systems, and clinical personas are out of scope for the
MVP unless a feature spec records a constitution-approved exception.

Rationale: The core risk is whether one CRM-owned prospect can produce a useful
disposition and follow-up task. Proving that loop matters more than breadth.

### III. Core, Adapters, and Personas Stay Separate
The Interaction Core MUST remain independent from ALF, nurse, doctor, CRM
vendor, telephony provider, and model-provider specifics. CRM integrations,
telephony transports, AI runtimes, and persona behavior MUST be implemented
behind explicit boundaries. Persona modules MUST own conversation goals,
disclosure language, allowed claims, extraction schema, disposition rules, and
escalation rules. Infrastructure code MUST NOT hardcode sales, clinical, or ALF
conversation behavior.

Rationale: openCloser is intended to support multiple personas and media
transports over time. Boundaries protect that path while keeping the MVP small.

### IV. Automation Is Auditable and Idempotent
Every automated attempt MUST produce traceable state, structured outcome data,
and enough correlation identifiers to debug queue item, session, provider call,
persona version, and CRM write-back behavior. External callbacks and write-back
jobs MUST be idempotent. Duplicate provider or mock events MUST NOT create
duplicate Phone Call activities, duplicate Tasks, duplicate attempt counts, or
conflicting final dispositions.

Features touching queue claims, provider callbacks, persona results, or
write-back MUST include focused verification for duplicate events, failed
events, blocked attempts, and retry behavior.

Rationale: Outreach automation is only useful if operators can trust what
happened and safely recover from provider, runtime, or CRM failures.

### V. Safety, Privacy, and Human Handoff Are Required Paths
Automated conversations MUST stay within the persona's approved scope. The ALF
MVP persona MUST disclose that it is an AI assistant calling on behalf of Medx,
MUST remain non-clinical, MUST NOT collect resident or patient health
information, and MUST stop after clear do-not-call or opt-out requests.
Features MUST preserve call windows, attempt limits, opt-out/DNC handling,
human-review reasons, and callback or review task creation for interested or
uncertain outcomes.

Clinical personas, patient-facing medical workflows, app video visits, and
avatar behavior require a separate PRD, safety model, escalation plan, and
constitution review before implementation.

Rationale: Human handoff and safety gates are part of the product, not edge
cases to be added after automation works.

## Architecture Constraints

The default implementation stack is Python 3.11 or newer, FastAPI, a simple
async worker, typed configuration from files plus environment secrets, SQLite or
local artifacts for Slice 1, Dynamics 365 / Dataverse for Slices 2 and 3,
`httpx`, pytest, a mock call transport for Slices 1 and 2, SignalWire for the
first production telephony transport, Pipecat for the voice runtime, and a
configured real-time AI provider for the first real-call path.

The MVP MUST avoid Celery, Redis as a required dependency, Kubernetes, multiple
CRM adapters, multiple telephony providers, frontend frameworks, analytics
dashboards, transcript review consoles, opportunity creation, advanced retry
orchestration, and custom product UI until the thin MVP loop is proven.

Secrets MUST come from environment variables or a secret manager. Logs MUST
avoid secrets and MUST minimize sensitive data. Transcript retention MUST be
deployment-configurable and MUST allow pointer-only or summary-only policies.

CRM schema and live Dataverse behavior MUST be verified before adding fields,
picklist values, or bulk updates. CRM data updates MUST preserve existing
high-confidence CRM values unless the feature explicitly requires and verifies
an overwrite policy.

## Delivery Workflow

Feature specs MUST define independently testable user stories and state how
each story advances the openCloser loop. Plans MUST pass the Constitution Check
before research and again after design. Tasks MUST preserve independent slices
and mark parallel work only when write sets and dependencies do not conflict.

Implementation plans MUST include:

- Target MVP slice or post-MVP phase.
- Queue source and CRM/write-back target.
- Mock or real call transport.
- Persona and persona versioning impact.
- Eligibility, DNC/opt-out, and call-window behavior.
- Structured result and CRM write-back behavior.
- Idempotency keys or duplicate-event handling.
- Human handoff behavior.
- Verification evidence, including unit, contract, integration, fixture, or
  manual demo checks appropriate to the risk.

No feature is complete until its acceptance criteria, relevant tests or demo
checks, and required documentation updates are completed.

## Governance

This constitution supersedes conflicting implementation habits, generated
template defaults, and local agent preferences. Product specs and architecture
docs may add detail, but they MUST NOT weaken these principles without a
constitution amendment.

Amendments MUST update this file, include a Sync Impact Report, update affected
Spec Kit templates or runtime guidance, and state the version bump rationale.
Semantic versioning applies:

- MAJOR for principle removals, incompatible governance changes, or permission
  to bypass CRM-first/product-safety rules.
- MINOR for new principles, materially expanded sections, or new required
  delivery gates.
- PATCH for clarifications that do not change required behavior.

All feature plans, task sets, and reviews MUST explicitly check constitution
compliance. Any accepted violation MUST be recorded in the plan's Complexity
Tracking section with the reason and the simpler alternative that was rejected.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
