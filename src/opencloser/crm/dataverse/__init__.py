"""Dataverse CRM adapter package — Slice 2.

All Dynamics 365 / Dataverse vendor detail — logical names, required lookups,
option-set values, and owner/team IDs — is confined to this package per spec
FR-016 and SC-010. Consumer code (orchestrator, eligibility, transport, persona)
stays vendor-neutral.

See specs/002-mock-call-real-crm/contracts/dataverse-adapter.md.
"""

from __future__ import annotations
