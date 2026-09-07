"""Shared helper for running real type checkers against a fixture file."""

import sys
from pathlib import Path
from subprocess import CompletedProcess, run

import pytest

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
