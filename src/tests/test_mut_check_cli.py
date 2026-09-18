"""`immut` requires an explicit `check` subcommand, matching `ruff check`/`ty check`."""

import subprocess
import sys

from _checkers import FIXTURES_DIR, REPO_ROOT

FIXTURE = FIXTURES_DIR / "mut_check_rejects_aliased_t.py"
NO_MUT_IN_SCOPE = FIXTURES_DIR / "mut_check_untyped_ratchet_no_mut_in_scope.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mut_check.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_check_subcommand_runs_the_static_check() -> None:
    result = run_cli("check", str(FIXTURE))

    assert result.returncode != 0
    assert "MutMarker" in result.stdout


def test_bare_invocation_prints_usage_and_fails() -> None:
    result = run_cli()

    assert result.returncode == 2
    assert "usage: immut check" in result.stderr


def test_unknown_subcommand_prints_usage_and_fails() -> None:
    result = run_cli("frobnicate", str(FIXTURE))

    assert result.returncode == 2
    assert "usage: immut check" in result.stderr


def test_untyped_flag_defaults_to_permissive() -> None:
    """A scope with no `Mut` is skipped by default -- see `mut_check._reassignment`'s docstring."""
    result = run_cli("check", str(NO_MUT_IN_SCOPE))

    assert result.returncode == 0
    assert "All checks passed!" in result.stdout


def test_untyped_strict_flag_disables_the_ratchet() -> None:
    result = run_cli("check", "--untyped=strict", str(NO_MUT_IN_SCOPE))

    assert result.returncode != 0
    assert "reassignment-without-mut" in result.stdout


def test_untyped_invalid_value_prints_usage_and_fails() -> None:
    result = run_cli("check", "--untyped=bogus", str(NO_MUT_IN_SCOPE))

    assert result.returncode == 2
    assert "usage: immut check" in result.stderr
