"""Pins confirmed, still-open `ty` bugs found while vendoring the patched
typeshed fork's `Mut`-aware stdlib container stubs, so an upstream fix shows
up here as a failing test instead of going unnoticed -- same pattern as
test_mut_self_mypy_bug.py for a mypy quirk.

Uses `mut_check._ty.run` directly, bypassing `mut_check.check`'s filters --
neither bug has a `mut_check`-layer exemption (a subscript-assignment one
was tried and found unsound, see docs/decisions.md's "Open `ty` bug:
subscript syntax..." section; the `Self`-in-`Intersection` one is worked
around in the stub itself instead, not filtered), so this pins raw `ty`
output, not `mut_check`'s.
"""

from _checkers import FIXTURES_DIR

# noinspection protected-member
from mut_check import _ty

SUBSCRIPT_ASSIGNMENT_BUG = FIXTURES_DIR / "mut_check_ty_bug_subscript_assignment.py"
SELF_IN_INTERSECTION_BUG = FIXTURES_DIR / "mut_check_ty_bug_self_in_intersection.py"


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
    """
    diagnostics = _ty.run(SELF_IN_INTERSECTION_BUG)
    text = "\n\n".join(d.text for d in diagnostics)

    assert len(diagnostics) == 1, text
    assert diagnostics[0].code == "invalid-argument-type"
    assert "does not satisfy upper bound" in text
    assert "of type variable `Self`" in text


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
