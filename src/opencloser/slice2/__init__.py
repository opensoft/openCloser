"""Slice 2 CLI-level coordination — run-mode handling and resume.

This package is a **boundary scaffold only** in the foundation PR — the runner
and resume-coordinator modules land in the US1/US2/US4 phases (sub-PRs #5, #6,
and subsequent work). The eventual package will wrap the unchanged Slice 1
orchestrator (spec FR-014): selecting dry-run vs. write-enabled mode, running
readiness/metadata verification, and driving the resume coordinator after a
transient write-back failure.

See specs/002-mock-call-real-crm/contracts/cli-slice2.md.
"""

from __future__ import annotations
