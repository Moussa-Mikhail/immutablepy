"""Pins confirmed, still-open `ty` bugs found while vendoring the patched
typeshed fork's `Mut`-aware stdlib container stubs, so an upstream fix shows
up here as a failing test instead of going unnoticed -- same pattern as
test_mut_self_mypy_bug.py for a mypy quirk.

Uses `mut_check._ty.run` directly, bypassing `mut_check.check`'s filters --
neither bug has a `mut_check`-layer exemption (a subscript-assignment one
was tried and found unsound, see docs/decisions.md's "Open `ty` bug:
subscript syntax..." section; the `Self`-in-`Intersection` one is worked
around in the stub itself instead, not filtered), so this pins raw `ty`
output, not `mut_check`'s -- except `test_ty_rejects_mut_self_on_generic_class`,
which deliberately goes through plain `ty check` (via `run_checker`, like
test_mut_self_mypy_bug.py) against the *public*, transparent `Mut[T] = T`
alias: that bug isn't specific to this tool's private `Intersection`-based
backend at all, so it needs to be pinned under the public-facing setup real
users' own `ty` would hit, not just internally.
"""

from _checkers import FIXTURES_DIR, run_checker

# noinspection protected-member
from mut_check import _ty

SUBSCRIPT_ASSIGNMENT_BUG = FIXTURES_DIR / "mut_check_ty_bug_subscript_assignment.py"
SELF_IN_INTERSECTION_BUG = FIXTURES_DIR / "mut_check_ty_bug_self_in_intersection.py"
SELF_GENERIC_CLASS_BUG = FIXTURES_DIR / "mut_self_generic_class_ty_bug.py"


def test_ty_still_rejects_self_in_intersection_on_mut_receiver() -> None:
    """`self: Mut[Self]` on a parameterized generic class, called on a
    genuinely `Mut[Box[int]]` receiver, should type-check clean -- `Self`
    inside an `Intersection` fails to substitute the enclosing class's type
    parameter before checking it against `Self`'s upper bound, so it
    doesn't. Worked around project-wide in the stdlib container stubs with
    `self: Mut[S]` (`S` a bound `TypeVar`) instead of `Self` -- see
    `list.S` in stubs/typeshed/stdlib/builtins.pyi.

    If this test starts failing, `ty` has fixed `Self` substitution inside
    `Intersection` -- the `Mut[S]` workaround would no longer be *necessary*
    (though there's no pressing reason to revert it either; it works
    correctly regardless of whether this bug is fixed).

    Narrower framing than the name suggests, confirmed separately: this
    isn't really about `Intersection` at all -- `Self` through *any* PEP 695
    generic type alias applied to a generic class triggers it, even the
    identity alias (`type Mut[T] = T`, no `Intersection` involved). See
    `test_ty_rejects_mut_self_on_generic_class` below for that broader,
    public-facing shape.
    """
    diagnostics = _ty.run(SELF_IN_INTERSECTION_BUG)
    text = "\n\n".join(d.text for d in diagnostics)

    assert len(diagnostics) == 1, text
    assert diagnostics[0].code == "invalid-argument-type"
    assert "does not satisfy upper bound" in text
    assert "of type variable `Self`" in text


def test_ty_rejects_mut_self_on_generic_class() -> None:
    """`self: Mut[Self]` on a *generic* class, called on a genuinely
    `Mut[Box[int]]` receiver, is incorrectly rejected by plain `ty` even
    under the public, transparent `Mut[T] = T` alias -- confirmed this has
    nothing to do with `Intersection` at all (the identity alias alone
    triggers it) and nothing to do with this tool's private backend (plain
    `ty check` against the public alias reproduces it identically). The
    otherwise-identical pattern on a non-generic class (`Counter`, in
    test_mut_self_mypy_bug.py and the `self_requires_mut_*` fixtures) is
    unaffected -- confirmed the class being generic is what triggers this.

    None of this project's own fixtures exercised `Mut[Self]` on a generic
    class before this test -- only the stdlib container stubs (`list[_T]`,
    `dict[_KT, _VT]`, `set[_T]`) did, which is why this was found there and
    not in any hand-written test here.

    If this test starts failing, `ty` has fixed `Self` substitution through
    a generic type alias for a generic class -- revisit whether `mut_method`
    is still needed for this case (a workaround for a *different*, unrelated
    mypy bug, per test_mut_self_mypy_bug.py -- but worth re-checking once
    this one's fixed too).
    """
    result = run_checker(["ty", "check"], SELF_GENERIC_CLASS_BUG)

    assert result.returncode != 0
    assert "does not satisfy upper bound" in result.stdout
    assert "of type variable `Self`" in result.stdout


def test_ty_still_rejects_subscript_assignment_on_mut_receiver() -> None:
    """`xs[0] = 1` on a genuinely `Mut[list[int]]` receiver should type-check
    clean -- the equivalent `xs.__setitem__(0, 1)` call does, on the
    identical receiver (see mut_check_stdlib_container_mutation_ok.py) --
    but `ty`'s subscript-assignment special form doesn't consult the
    receiver's `Mut`-intersection self-typing at all, so it doesn't.

    If this test starts failing, `ty` has fixed its subscript-assignment
    resolution -- worth revisiting whether the natural syntax is usable
    again, and whether a `mut_check`-layer exemption would now be safe (the
    earlier attempt wasn't just permission-blind: `ty` couldn't validate the
    *assigned value* either once the receiver carried `MutMarker`, so a
    wrong element type or an unrelated type mismatch produced the identical
    diagnostic shape as this false positive -- confirm that's fixed too,
    not just this exact case, before reintroducing one).
    """
    diagnostics = _ty.run(SUBSCRIPT_ASSIGNMENT_BUG)
    text = "\n\n".join(d.text for d in diagnostics)

    assert len(diagnostics) == 1, text
    assert diagnostics[0].code == "invalid-assignment"
    assert "Invalid subscript assignment" in text
    assert "The full type of the subscripted object is" in text
