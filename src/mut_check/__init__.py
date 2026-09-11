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
"""

from pathlib import Path

from mut_check import _ty
from mut_check._diagnostics import Diagnostic
from mut_check._filter import filter_construction_exemption
from mut_check._immutable import filter_immutable_type_exemption

__all__ = ["Diagnostic", "check"]


def check(*paths: str | Path) -> list[Diagnostic]:
    """Run the private static check against `paths`, returning the filtered diagnostics."""
    return filter_immutable_type_exemption(filter_construction_exemption(_ty.run(*paths)))
