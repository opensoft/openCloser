"""Transcript redaction boundary — Slice 2.

This package carries the import-time contract (`tests/test_imports.py`) and
the ``RedactionLayer`` implementation in ``layer.py``. The layer transforms
transcript text before any transcript artifact is written to disk (spec
FR-028, FR-029, FR-030); default-on; configurable via the ``[redaction]``
section of config/slice2.toml.

See specs/002-mock-call-real-crm/contracts/redaction-layer.md.
"""

from __future__ import annotations
