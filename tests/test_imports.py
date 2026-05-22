"""T067 — Dependency-direction lint (SC-009 module-isolation gate).

Walks the AST of every `src/opencloser/**/*.py` and asserts the FR-033 boundary's
dependency-allowed rules from `contracts/*.md` hold. Per boundary:

- ``core`` may import any boundary module + state + models + artifacts.
- ``eligibility`` / ``transport`` / ``persona`` MAY import `models` and shared
  `core` primitives (`ids`, `clock`, `idempotency` per orchestrator contract),
  but MUST NOT import each other.
- ``crm`` may import `models` and `state` only — `contracts/crm-writeback.md`
  explicitly forbids `core` for the write-back boundary.
- ``artifacts`` writer may import `models` only.
- ``state`` may import `models` only.

Each group may also import its own submodules — intra-boundary imports
(e.g. `opencloser.transport.mock` importing `opencloser.transport.base`) are not
cross-boundary violations.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

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
        "opencloser.eligibility",  # intra-boundary submodules
    },
    "transport": {
        "opencloser.models",
        "opencloser.core",
        "opencloser.transport",  # intra-boundary submodules
    },
    "persona": {
        "opencloser.models",
        "opencloser.core",
        "opencloser.persona",  # intra-boundary submodules
    },
    "crm": {
        "opencloser.models",
        "opencloser.state",  # adapter persists; allowed
        "opencloser.crm",  # intra-boundary submodules
    },
    "state": {
        "opencloser.models",
        "opencloser.state",  # intra-boundary submodules
    },
    "artifacts": {
        "opencloser.models",
        "opencloser.artifacts",  # intra-boundary submodules
    },
}


# Top-level files living directly under `src/opencloser/` (not inside an FR-033
# boundary package). These are intentionally EXEMPT from the dependency-direction
# lint, each for a documented reason:
#   - `cli.py`    — the operator entrypoint; it composes the concrete implementations
#                   of every boundary by design (that is its job, per FR-025).
#   - `models.py` — the shared Pydantic layer that every boundary is allowed to import.
#   - `__init__.py` — the `opencloser` package root; it carries no cross-boundary imports.
# The exemption is explicit (not a silent `group is None` skip): any NEW top-level
# file will fail `test_dependency_directions_respect_contracts` until a reviewer
# either adds it here with a rationale or moves it into a boundary package.
_TOP_LEVEL_EXEMPT: set[str] = {"cli.py", "models.py", "__init__.py"}


def _python_files(root: Path) -> Iterable[Path]:
    # `__init__.py` files are NOT skipped — a forbidden cross-boundary import must not
    # be able to hide in a package root (SC-009).
    yield from root.rglob("*.py")


def _module_group(rel_path: Path) -> str | None:
    parts = rel_path.parts
    # rel_path is relative to src/opencloser/. The top-level directory is the boundary group.
    if len(parts) >= 2:
        return parts[0]
    return None


def _collect_imports(tree: ast.AST) -> tuple[set[str], list[int]]:
    """Return (absolute imported module names, line numbers of relative imports).

    Relative imports (`from . import x` / `from ..bar import y`) carry no absolute
    module path, so the allowlist match below cannot see them — a cross-boundary
    `from ..persona import X` would silently bypass the SC-009 gate. They are
    collected separately and rejected outright (the codebase uses absolute imports).
    """
    names: set[str] = set()
    relative_lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                relative_lines.append(node.lineno)
            elif node.module == "opencloser":
                # `from opencloser import X` — X names a submodule; expand to
                # `opencloser.X` so the boundary check sees it (bare "opencloser"
                # would otherwise slip past the `opencloser.` prefix filter).
                for alias in node.names:
                    names.add(f"opencloser.{alias.name}")
            elif node.module:
                names.add(node.module)
    return names, relative_lines


def test_dependency_directions_respect_contracts() -> None:
    violations: list[str] = []
    for path in _python_files(_SRC):
        rel = path.relative_to(_SRC)
        group = _module_group(rel)
        if group is None:
            # A top-level file directly under src/opencloser/. These are exempt from the
            # lint, but only via the explicit allow-list — an unrecognized one is an error.
            assert path.name in _TOP_LEVEL_EXEMPT, (
                f"unexpected top-level file {path.name!r} under src/opencloser/ — add it "
                f"to _TOP_LEVEL_EXEMPT with a rationale, or move it into a boundary package"
            )
            continue
        if group not in _ALLOWED:
            violations.append(
                f"{rel}: unknown boundary group {group!r} — add it to _ALLOWED with its "
                f"dependency rules, or move the file into an existing boundary package"
            )
            continue
        allowed = _ALLOWED[group]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported, relative_lines = _collect_imports(tree)
        for lineno in relative_lines:
            violations.append(
                f"{rel}:{lineno}: relative import bypasses the dependency-direction "
                f"gate — use an absolute `opencloser.*` import"
            )
        for imp in imported:
            if imp == "opencloser":
                violations.append(
                    f"{rel}: bare `import opencloser` — import the specific submodule so "
                    f"the dependency-direction gate can see what is used"
                )
                continue
            if not imp.startswith("opencloser."):
                continue  # stdlib + third-party are unrestricted
            if not any(imp == ok or imp.startswith(ok + ".") for ok in allowed):
                violations.append(f"{rel}: imports {imp} (group={group})")
    assert not violations, "Dependency-direction violations:\n" + "\n".join(violations)


@pytest.mark.module("imports")
def test_each_boundary_module_compiles_without_cross_imports() -> None:
    """Smoke check: simply ensure every src/opencloser/**/*.py parses as valid Python."""
    for path in _python_files(_SRC):
        ast.parse(path.read_text(encoding="utf-8"))
