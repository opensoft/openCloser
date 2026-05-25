"""Slice 2 CLI-level coordination — run-mode handling and resume.

This package wraps the unchanged Slice 1 orchestrator (spec FR-014):
selecting dry-run vs. write-enabled mode, running readiness/metadata
verification, and driving the resume coordinator after a transient
write-back failure. Surface modules:

  * ``runner.py`` — ``run_one_crm_item`` end-to-end runner, readiness
    gates, and the ``CrmRunReport`` exit shape (T024-T029, T030+).
  * ``resume.py`` — ``resume_session`` coordinator for the FR-023
    ``resume_needed`` recovery path (T032+).

See specs/002-mock-call-real-crm/contracts/cli-slice2.md.
"""

from __future__ import annotations
