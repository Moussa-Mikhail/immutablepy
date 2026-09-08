"""Shared helper for running real type checkers against a fixture file."""

import sys
from collections.abc import Sequence
from pathlib import Path
from subprocess import CompletedProcess, run

import pytest

from mut_check import Diagnostic

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

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


def diagnostics_text(diagnostics: Sequence[Diagnostic]) -> str:
    """Join diagnostics into one searchable block, for substring assertions."""
    return "\n\n".join(d.text for d in diagnostics)


def is_clean(diagnostics: Sequence[Diagnostic]) -> bool:
    """Whether `diagnostics` contains nothing that should fail a check."""
    return not any(d.is_blocking() for d in diagnostics)
