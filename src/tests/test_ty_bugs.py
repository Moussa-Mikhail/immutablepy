"""Pins a confirmed, still-open `ty` bug found while vendoring the patched
typeshed fork's `Mut`-aware stdlib container stubs, so an upstream fix shows
up here as a failing test instead of going unnoticed -- same pattern as
test_mut_self_mypy_bug.py for a mypy quirk.

`ty`'s other two Self-through-generic-type-alias bugs
(`test_ty_still_rejects_self_in_intersection_on_mut_receiver` and
`test_ty_rejects_mut_self_on_generic_class`, pinning
mut_check_ty_bug_self_in_intersection.py and mut_self_generic_class_ty_bug.py)
were retired here: fixed upstream by astral-sh/ruff#28890 (commit `162c08c`),
confirmed by building `ty` from that commit and seeing both tests fail as
their docstrings predicted. No release includes the fix yet -- see
docs/decisions.md's "`ty` bug: `Self` doesn't substitute through a generic
type alias" section for the full trail and the status to watch for. The
`Mut[S]` stub workaround (`list.S` etc. in stubs/typeshed/stdlib/builtins.pyi)
stays regardless; reverting it to `Mut[Self]` would be possible once a
release ships but has no benefit.

Uses `mut_check._ty.run` directly, bypassing `mut_check.check`'s filters --
this bug has no `mut_check`-layer exemption (a subscript-assignment one was
tried and found unsound, see docs/decisions.md's "Open `ty` bug: subscript
syntax..." section), so this pins raw `ty` output, not `mut_check`'s.
"""

from _checkers import FIXTURES_DIR

# noinspection protected-member
from mut_check import _ty

SUBSCRIPT_ASSIGNMENT_BUG = FIXTURES_DIR / "mut_check_ty_bug_subscript_assignment.py"


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
