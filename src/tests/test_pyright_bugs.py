"""Pins pyright's current bug on a `Mut[...]`-typed instance attribute as a
known limitation.

pyright rejects `self.items: Mut[list[int]] = []` in `__init__` with
"Attribute type cannot use type variable ... scoped to local method" --
it treats the public, transparent `type Mut[T] = T` alias's own type
parameter as bound to the local application site, not valid for a
persisting instance attribute. Confirmed to be a pyright bug, not a real
constraint (mypy and `ty` both accept this fine) -- distinct from every
other cross-checker `Mut`/`Self` quirk found this session (mypy's
`self: Mut[Self]` rejection in mut_self_mypy_bug.py; ty's generic-alias
`Self`-substitution and subscript-assignment bugs in test_ty_bugs.py):
this one has nothing to do with `Self` at all, it's about an ordinary
attribute annotation.

If pyright ever stops erroring here, this test starts failing -- that's
the point: a signal the bug's been fixed, not a silent behavior change
nobody notices.
"""

from _checkers import FIXTURES_DIR, run_checker

FIXTURE = FIXTURES_DIR / "mut_attribute_pyright_bug.py"


def test_pyright_currently_rejects_mut_attribute() -> None:
    result = run_checker(["pyright"], FIXTURE)

    assert result.returncode != 0
    assert "Attribute type cannot use type variable" in result.stdout
    assert "scoped to local method" in result.stdout


def test_mypy_accepts_mut_attribute() -> None:
    result = run_checker(["mypy"], FIXTURE)

    assert result.returncode == 0, result.stdout + result.stderr


def test_ty_accepts_mut_attribute() -> None:
    result = run_checker(["ty", "check"], FIXTURE)

    assert result.returncode == 0, result.stdout + result.stderr
