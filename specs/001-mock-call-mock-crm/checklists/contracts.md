# Contracts Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of the five module-boundary contract documents in `contracts/`. Unit tests for the *contract writing*, not for the implementation.

**Created**: 2026-05-19
**Contracts**: [orchestrator](../contracts/orchestrator.md) ; [eligibility](../contracts/eligibility.md) ; [transport](../contracts/transport.md) ; [persona](../contracts/persona.md) ; [crm-writeback](../contracts/crm-writeback.md)

## Contract Completeness

- [x] CHK001 - Does each of the five contract files exist and correspond 1:1 to a FR-033 module boundary? [Completeness, Plan §Project Structure + Spec §FR-033]
- [x] CHK002 - Does every contract specify a Public Surface section with concrete method signatures (inputs, outputs)? [Completeness, Contracts]
- [x] CHK003 - Does every contract enumerate Dependencies-Allowed AND Dependencies-Forbidden lists? [Completeness, Contracts]
- [x] CHK004 - Does each contract state which spec FRs it implements (traceability to spec)? [Traceability, Contracts]
- [x] CHK005 - Does the orchestrator contract specify session lifecycle states and transitions? [Completeness, Contracts §orchestrator.md]
- [x] CHK006 - Does the orchestrator contract specify the idempotency-key application algorithm (compute → check → INSERT-or-skip)? [Completeness, Contracts §orchestrator.md + Spec §FR-019]
- [x] CHK007 - Does the eligibility contract specify behavior on the default-timezone fallback (which rule passes; what field records the substitution)? [Completeness, Contracts §eligibility.md + Spec §Edge Cases]
- [x] CHK008 - Does the transport contract specify the event-emission schema (event_id, type, timestamp, payload)? [Completeness, Contracts §transport.md]
- [x] CHK009 - Does the persona contract specify the FR-036 disposition precedence as a numbered list? [Completeness, Contracts §persona.md + Spec §FR-036]
- [x] CHK010 - Does the persona contract specify the FR-035 escalation reason-code enumeration verbatim (9 codes)? [Completeness, Contracts §persona.md + Spec §FR-035]
- [x] CHK011 - Does the crm-writeback contract enumerate the FR-031 per-disposition emission map AND the FR-032 per-disposition new_status map? [Completeness, Contracts §crm-writeback.md + Spec §FR-031 / §FR-032]
- [x] CHK012 - Does the crm-writeback contract specify FR-018's belt-and-suspenders behavior at the adapter (`emit_task` no-ops for excluded dispositions)? [Completeness, Contracts §crm-writeback.md + Spec §FR-018]

## Contract Clarity

- [x] CHK013 - Are method signatures in each contract language-neutral (no Python-specific syntax) so a future re-implementation in another language could satisfy them? [Clarity, Contracts]
- [x] CHK014 - Are input/output types named with the same Pydantic class names as in `data-model.md` (so the cross-reference is exact)? [Consistency, Contracts + Plan §data-model.md]
- [x] CHK015 - Are "Owns" and "MUST NOT contain" sections in each contract specific enough to gate code review (concrete examples per side)? [Clarity, Contracts]
- [x] CHK016 - Is "conceptual contract" defined the same way across `transport.md` (FR-008) and `crm-writeback.md` (FR-016) contracts? [Consistency, Contracts]

## Contract Consistency

- [x] CHK017 - Are the dependency-direction rules in the contracts consistent with the proposed `tests/test_imports.py` lint (research.md §Tests)? [Consistency, Contracts + Research §Tests]
- [x] CHK018 - Does the orchestrator contract's "owns idempotency" claim align with research.md's idempotency-check-ordering decision? [Consistency, Contracts §orchestrator.md + Research §Cross-cutting]
- [x] CHK019 - Do the transport.md + persona.md contracts agree on who initiates the persona's first turn after `connected` (transport vs. orchestrator vs. persona)? [Consistency, Contracts §transport.md + §persona.md]
- [x] CHK020 - Do the persona.md disposition-rule precedence and the crm-writeback.md emission map produce a consistent overall behavior (every disposition produced by the persona maps cleanly through the writeback)? [Consistency, Contracts §persona.md + §crm-writeback.md]

## Forward Compatibility

- [x] CHK021 - Does each contract that has a Slice 2 substitution (transport, crm-writeback, persona) state precisely which fields/methods are expected to be name-only changes vs. shape changes? [Forward-compat, Contracts + Spec §SC-008]
- [x] CHK022 - Is the SC-008 verification approach documented per contract (e.g., "Slice 2 plan-time review checks this contract against the Dataverse SDK")? [Traceability, Contracts §crm-writeback.md + Spec §SC-008]

## Acceptance Criteria Quality

- [x] CHK023 - Can each contract's "MUST NOT contain" list be enforced by static code analysis (dependency-direction lint) rather than only by code-review discipline? [Measurability, Contracts]
- [x] CHK024 - Is each contract's Public Surface concrete enough that a stub satisfying the interface can be auto-generated from the method signatures? [Measurability, Contracts + Spec §SC-009]
- [x] CHK025 - Is the contract's adherence verifiable at unit-test level (each module's unit tests stub all other modules using the contract's interface only)? [Measurability, Contracts + Spec §SC-009]
