"""
mut_check: the tool's own private, intersection-based static check.

Wraps the bundled `ty` binary, configured (via `_ty_project/ty.toml`) to
resolve `immutablepy` to the intersection-based internal stub
(`stubs/internal/`) instead of the plain public alias real type checkers
see. `ty` is an implementation detail of `mut_check._ty`; callers of `check`
shouldn't need to know it's `ty` underneath.

`check` returns structured `Diagnostic`s -- `severity`/`code`/`file`/`line`/
`col` for deciding what to keep (the filter) or how to fail (the CLI's exit
code), plus `text`: `ty`'s own diagnostic block verbatim, so `immut check`'s
output looks exactly like `ty check`'s. A future LSP server (per CLAUDE.md's
"Private ty backend") would drive `ty server` directly instead -- a separate
code path, since LSP `publishDiagnostics` needs `ty`'s clean structured
message, not this CLI-oriented rendered text.

Diagnostics come from two sources now: `ty` itself (filtered, as above), and
`mut_check._reassignment` -- the first piece of the not-yet-built custom
pass (per CLAUDE.md's "Open" items), which `ty` has no equivalent of at all.
"""

from pathlib import Path

from immutablepy import Mut
from mut_check import _ty
from mut_check._diagnostics import Diagnostic
from mut_check._filter import filter_construction_exemption
from mut_check._immutable import filter_immutable_type_exemption
from mut_check._reassignment import find_unpermitted_reassignments

__all__ = ["Diagnostic", "check"]


def _iter_python_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.rglob("*.py"))


def check(*paths: str | Path) -> list["Diagnostic"]:
    """Run the private static check against `paths`, returning the filtered diagnostics."""
    ty_diagnostics = get_ty_diagnostics(paths)

    custom_diagnostics = get_custom_diagnostics(paths)

    return ty_diagnostics + custom_diagnostics


def get_custom_diagnostics(paths: tuple[str | Path, ...]) -> list[Diagnostic]:
    custom_diagnostics = []
    for path in paths:
        for file in _iter_python_files(Path(path)):
            custom_diagnostics.extend(find_unpermitted_reassignments(file))

    return custom_diagnostics


def get_ty_diagnostics(paths: tuple[str | Path, ...]) -> list[Diagnostic]:
    filters = (filter_construction_exemption, filter_immutable_type_exemption)
    ty_diagnostics: Mut[list[Diagnostic]] = _ty.run(*paths)

    for f in filters:
        ty_diagnostics = f(ty_diagnostics)
    return ty_diagnostics
