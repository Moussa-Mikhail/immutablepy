"""
mut_check: the tool's own private, intersection-based static check.

Wraps the bundled `ty` binary, configured (via `_ty_project/ty.toml`) to
resolve `immutablepy` to the intersection-based internal stub
(`stubs/internal/`) instead of the plain public alias real type checkers
see. `ty` is an implementation detail of `mut_check._ty`; callers of `check`
shouldn't need to know it's `ty` underneath.

`check` returns structured `Diagnostic`s rather than raw text, so the same
result can drive multiple frontends -- today a CLI (`immut check`,
human-readable text), eventually an LSP server (per CLAUDE.md's "Private ty
backend", `publishDiagnostics` JSON) -- without either needing to parse the
other's output shape.
"""

from pathlib import Path

from mut_check import _ty
from mut_check._diagnostics import Diagnostic
from mut_check._filter import filter_construction_exemption

__all__ = ["Diagnostic", "check"]


def check(*paths: str | Path) -> list[Diagnostic]:
    """Run the private static check against `paths`, returning the filtered diagnostics."""
    return filter_construction_exemption(_ty.run(*paths))
