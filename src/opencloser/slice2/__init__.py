"""Slice 2 CLI-level coordination — run-mode handling and resume.

This package wraps the unchanged Slice 1 orchestrator (spec FR-014): it selects
dry-run vs. write-enabled mode, runs readiness/metadata verification, and drives
the resume coordinator after a transient write-back failure.

See specs/002-mock-call-real-crm/contracts/cli-slice2.md.
"""

from __future__ import annotations
