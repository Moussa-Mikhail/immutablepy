"""Pins mypy's current bug on `self: Mut[Self]` as a known limitation.

If mypy ever stops erroring here, this test starts failing -- that's the
point: it's a signal to revisit whether `mut_method` is still needed as a
workaround, rather than a silent behavior change nobody notices.
"""

from _checkers import FIXTURES_DIR, run_checker

FIXTURE = FIXTURES_DIR / "mut_self_mypy_bug.py"


def test_mypy_currently_rejects_mut_self() -> None:
    result = run_checker(["mypy"], FIXTURE)

    assert result.returncode != 0
    assert "Method cannot have explicit self annotation and Self type" in result.stdout


def test_pyright_accepts_mut_self() -> None:
    result = run_checker(["pyright"], FIXTURE)

    assert result.returncode == 0, result.stdout + result.stderr


def test_ty_accepts_mut_self() -> None:
    result = run_checker(["ty", "check"], FIXTURE)

    assert result.returncode == 0, result.stdout + result.stderr
