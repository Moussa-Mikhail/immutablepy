"""Shared helper for running real type checkers against a fixture file."""

import sys
from pathlib import Path
from subprocess import CompletedProcess, run

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
INTERNAL_TY_PROJECT = Path(__file__).resolve().parent / "internal_ty_project"

CHECKERS = [
    pytest.param(["mypy"], id="mypy"),
    pytest.param(["pyright"], id="pyright"),
    pytest.param(["ty", "check"], id="ty"),
]


def run_checker(checker_args: list[str], fixture: Path) -> CompletedProcess[str]:
    """Run `checker_args` (e.g. `["mypy"]`) against `fixture` via `python -m`."""
    return run(
        [sys.executable, "-m", *checker_args, str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_internal_ty(fixture: Path) -> CompletedProcess[str]:
    """Run `ty` against `fixture` resolving `immutablepy` to the intersection-based
    internal stub (`stubs/internal/`), the same way the tool's bundled `ty` will be
    configured -- instead of the plain public alias real checkers see.
    """
    return run(
        [sys.executable, "-m", "ty", "check", "--project", str(INTERNAL_TY_PROJECT), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
