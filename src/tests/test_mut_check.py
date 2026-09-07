"""`mut_check` must actually gate `Mut[T]`.

Unlike the compatibility tests, these go through `mut_check.check` -- the
app's own entry point -- rather than the plain public alias real checkers
see. If any of these stopped holding, `Mut[T] <: T` enforcement would be
silently doing nothing, or the future diagnostic filter would be built
against a false picture of what the check actually reports.
"""

from _checkers import FIXTURES_DIR

from mut_check import check

REJECTS_ALIASED_T = FIXTURES_DIR / "mut_check_rejects_aliased_t.py"
ACCEPTS_MUT_WHERE_T_EXPECTED = FIXTURES_DIR / "mut_check_accepts_mut_where_t_expected.py"
GENERIC_SUBSTITUTION = FIXTURES_DIR / "mut_check_generic_substitution.py"
CONSTRUCTION_LITERAL = FIXTURES_DIR / "mut_check_construction_literal.py"
PREDECLARED_FOR_LOOP = FIXTURES_DIR / "mut_check_predeclared_for_loop.py"
PREDECLARED_WITH = FIXTURES_DIR / "mut_check_predeclared_with.py"
PREDECLARED_UNPACKING = FIXTURES_DIR / "mut_check_predeclared_unpacking.py"
CONTAINER_MUTABILITY_OK = FIXTURES_DIR / "mut_check_container_mutability_ok.py"
CONTAINER_MUTABILITY_BAD = FIXTURES_DIR / "mut_check_container_mutability_bad.py"
PROTOCOL_CONFORMANCE_BAD = FIXTURES_DIR / "mut_check_protocol_conformance_bad.py"
SELF_REQUIRES_MUT_OK = FIXTURES_DIR / "mut_check_self_requires_mut_ok.py"
SELF_REQUIRES_MUT_BAD = FIXTURES_DIR / "mut_check_self_requires_mut_bad.py"

MUT_MARKER_EXPLANATION = "not assignable to element `MutMarker`"


def test_aliased_plain_t_is_rejected_for_mut_position() -> None:
    result = check(REJECTS_ALIASED_T)

    assert result.returncode != 0
    assert "MutMarker" in result.stdout


def test_mut_is_accepted_where_plain_t_expected() -> None:
    """The forward direction of `Mut[T] <: T`: no filter is needed for this side."""
    result = check(ACCEPTS_MUT_WHERE_T_EXPECTED)

    assert result.returncode == 0, result.stdout + result.stderr


def test_intersection_survives_generic_substitution() -> None:
    """`Container[int].item` (declared `Mut[T]`) must reveal `int & MutMarker`, not `int`."""
    result = check(GENERIC_SUBSTITUTION)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "int & MutMarker" in result.stdout


def test_construction_literal_produces_marker_explanation() -> None:
    """Baseline for the future filter: today's exact false-positive shape for a literal."""
    result = check(CONSTRUCTION_LITERAL)

    assert result.returncode != 0
    assert MUT_MARKER_EXPLANATION in result.stdout
    assert "list[int] & MutMarker" in result.stdout


def test_predeclared_for_loop_lacks_marker_explanation() -> None:
    """Known gap: unlike plain assignment, the for-loop target's message never
    mentions `MutMarker` -- confirmed by inspecting the checker's diagnostics
    directly, not just its default rendering. A filter matching only on the
    `MutMarker` substring misses this.
    """
    result = check(PREDECLARED_FOR_LOOP)

    assert result.returncode != 0
    assert "is not assignable to `Mut[int]`" in result.stdout
    assert MUT_MARKER_EXPLANATION not in result.stdout
    assert "int & MutMarker" in result.stdout  # from reveal_type, not the error itself


def test_predeclared_with_lacks_marker_explanation() -> None:
    """Same gap as the for-loop case, for `with`-statement pre-declared targets."""
    result = check(PREDECLARED_WITH)

    assert result.returncode != 0
    assert "is not assignable to `Mut[StringIO]`" in result.stdout
    assert MUT_MARKER_EXPLANATION not in result.stdout
    assert "StringIO & MutMarker" in result.stdout  # from reveal_type, not the error itself


def test_predeclared_unpacking_has_marker_explanation() -> None:
    """Unlike for-loop/with, unpacking's message shape matches plain assignment."""
    result = check(PREDECLARED_UNPACKING)

    assert result.returncode != 0
    assert MUT_MARKER_EXPLANATION in result.stdout
    assert "int & MutMarker" in result.stdout


def test_container_mutability_is_compositional() -> None:
    """`Mut[list[User]]` grants container-only permission (plain elements accepted);
    `Mut[list[Mut[User]]]` additionally grants element-mutation permission (`Mut`
    elements accepted too). Both driven by real stdlib `list.append`, no custom
    stdlib stubs needed for this distinction.
    """
    result = check(CONTAINER_MUTABILITY_OK)

    assert result.returncode == 0, result.stdout + result.stderr


def test_container_mutability_rejects_plain_element_for_deeply_mut_list() -> None:
    """`Mut[list[Mut[User]]]` must reject a plain `User` element -- it's missing the
    element-level `MutMarker` that `Mut[list[User]]` alone would not have required.
    """
    result = check(CONTAINER_MUTABILITY_BAD)

    assert result.returncode != 0
    assert MUT_MARKER_EXPLANATION in result.stdout
    assert "User & MutMarker" in result.stdout


def test_protocol_conformance_catches_mut_mismatch() -> None:
    """A class with a plain field must fail to satisfy a Protocol declaring that
    field as `Mut` -- native structural conformance checking catches this with
    zero custom logic, per CLAUDE.md's "resolved by the intersection-type
    approach" note in the Protocols section.
    """
    result = check(PROTOCOL_CONFORMANCE_BAD)

    assert result.returncode != 0
    assert "not assignable to protocol `HasValue`" in result.stdout
    assert "protocol member `value` is incompatible" in result.stdout


def test_self_requires_mut_is_accepted_on_mut_receiver() -> None:
    """Control case: a `self: Mut[Self]` method called on a `Mut[...]` receiver
    must be accepted -- the receiver carries `MutMarker`.
    """
    result = check(SELF_REQUIRES_MUT_OK)

    assert result.returncode == 0, result.stdout + result.stderr


def test_self_requires_mut_is_rejected_on_plain_receiver() -> None:
    """A method declared `self: Mut[Self]` must reject being called on a plain
    (non-`Mut`) receiver -- this is what makes `Mut[Self]` actually gate mutating
    methods, not just document them.
    """
    result = check(SELF_REQUIRES_MUT_BAD)

    assert result.returncode != 0
    assert MUT_MARKER_EXPLANATION in result.stdout
    assert "Counter & MutMarker" in result.stdout
