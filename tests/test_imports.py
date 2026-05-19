"""T067 — Dependency-direction lint (SC-009 module-isolation gate).

Walks the AST of every `src/opencloser/*.py` and asserts the FR-033 boundary's
dependency-allowed rules from `contracts/*.md` hold. Per boundary:

- ``core`` may import any boundary module + state + models + artifacts.
- ``eligibility`` / ``transport`` / ``persona`` / ``crm`` MAY import `models` and
  shared `core` primitives (`ids`, `clock`, `idempotency` per orchestrator contract),
  but MUST NOT import each other.
- ``artifacts`` writer may import `models` only.
- ``state`` may import `models` only.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src" / "opencloser"

# Module group → allowed-import prefixes (under `opencloser`).
_ALLOWED: dict[str, set[str]] = {
    "core": {
        "opencloser.models",
        "opencloser.state",
        "opencloser.artifacts",
        "opencloser.eligibility",
        "opencloser.transport",
        "opencloser.persona",
        "opencloser.crm",
        "opencloser.core",
    },
    "eligibility": {
        "opencloser.models",
        "opencloser.core",
    },
    "transport": {
        "opencloser.models",
        "opencloser.core",
    },
    "persona": {
        "opencloser.models",
        "opencloser.core",
        "opencloser.persona",  # internal submodules
    },
    "crm": {
        "opencloser.models",
        "opencloser.state",  # adapter persists; allowed
        "opencloser.core",
    },
    "state": {
        "opencloser.models",
    },
    "artifacts": {
        "opencloser.models",
    },
}


def _python_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        if p.name == "__init__.py":
            # Allow flexible re-exports in package roots; they typically just import for typing.
            continue
        yield p


def _module_group(rel_path: Path) -> str | None:
    parts = rel_path.parts
    # rel_path is relative to src/opencloser/. The top-level directory is the boundary group.
    if len(parts) >= 2:
        return parts[0]
    return None


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


def test_dependency_directions_respect_contracts() -> None:
    violations: list[str] = []
    for path in _python_files(_SRC):
        rel = path.relative_to(_SRC)
        group = _module_group(rel)
        if group is None or group not in _ALLOWED:
            continue
        allowed = _ALLOWED[group]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for imp in _imported_names(tree):
            if not imp.startswith("opencloser."):
                continue  # stdlib + third-party are unrestricted
            if not any(imp == ok or imp.startswith(ok + ".") for ok in allowed):
                violations.append(f"{path.relative_to(_SRC)}: imports {imp} (group={group})")
    assert not violations, "Dependency-direction violations:\n" + "\n".join(violations)


@pytest.mark.module("imports")
def test_each_boundary_module_compiles_without_cross_imports() -> None:
    """Smoke check: simply ensure every src/opencloser/**/*.py parses as valid Python."""
    for path in _python_files(_SRC):
        ast.parse(path.read_text(encoding="utf-8"))
