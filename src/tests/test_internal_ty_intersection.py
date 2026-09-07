"""The tool's private, intersection-based `ty` view must actually gate `Mut[T]`.

Unlike the compatibility tests, these target `stubs/internal/` directly (via
`extra-paths`, exactly as the bundled `ty` will be configured) rather than the
plain public alias. If any of these stopped holding, `Mut[T] <: T` enforcement
would be silently doing nothing, or the future diagnostic filter would be
built against a false picture of what `ty` actually reports.
"""

from _checkers import FIXTURES_DIR, run_internal_ty

REJECTS_ALIASED_T = FIXTURES_DIR / "internal_view_rejects_aliased_t.py"
ACCEPTS_MUT_WHERE_T_EXPECTED = FIXTURES_DIR / "internal_view_accepts_mut_where_t_expected.py"
GENERIC_SUBSTITUTION = FIXTURES_DIR / "internal_view_generic_substitution.py"
CONSTRUCTION_LITERAL = FIXTURES_DIR / "internal_view_construction_literal.py"
PREDECLARED_FOR_LOOP = FIXTURES_DIR / "internal_view_predeclared_for_loop.py"
PREDECLARED_WITH = FIXTURES_DIR / "internal_view_predeclared_with.py"
PREDECLARED_UNPACKING = FIXTURES_DIR / "internal_view_predeclared_unpacking.py"
CONTAINER_MUTABILITY_OK = FIXTURES_DIR / "internal_view_container_mutability_ok.py"
CONTAINER_MUTABILITY_BAD = FIXTURES_DIR / "internal_view_container_mutability_bad.py"
PROTOCOL_CONFORMANCE_BAD = FIXTURES_DIR / "internal_view_protocol_conformance_bad.py"

MUT_MARKER_EXPLANATION = "not assignable to element `MutMarker`"


def test_aliased_plain_t_is_rejected_for_mut_position() -> None:
    result = run_internal_ty(REJECTS_ALIASED_T)

    assert result.returncode != 0
    assert "MutMarker" in result.stdout


def test_mut_is_accepted_where_plain_t_expected() -> None:
    """The forward direction of `Mut[T] <: T`: no filter is needed for this side."""
    result = run_internal_ty(ACCEPTS_MUT_WHERE_T_EXPECTED)

    assert result.returncode == 0, result.stdout + result.stderr


def test_intersection_survives_generic_substitution() -> None:
    """`Container[int].item` (declared `Mut[T]`) must reveal `int & MutMarker`, not `int`."""
    result = run_internal_ty(GENERIC_SUBSTITUTION)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "int & MutMarker" in result.stdout


def test_construction_literal_produces_marker_explanation() -> None:
    """Baseline for the future filter: today's exact false-positive shape for a literal."""
    result = run_internal_ty(CONSTRUCTION_LITERAL)

    assert result.returncode != 0
    assert MUT_MARKER_EXPLANATION in result.stdout
    assert "list[int] & MutMarker" in result.stdout


def test_predeclared_for_loop_lacks_marker_explanation() -> None:
    """Known gap: unlike plain assignment, the for-loop target's message never
    mentions `MutMarker` -- confirmed via raw LSP `publishDiagnostics`, not just
    CLI rendering. A filter matching only on the `MutMarker` substring misses this.
    """
    result = run_internal_ty(PREDECLARED_FOR_LOOP)

    assert result.returncode != 0
    assert "is not assignable to `Mut[int]`" in result.stdout
    assert MUT_MARKER_EXPLANATION not in result.stdout
    assert "int & MutMarker" in result.stdout  # from reveal_type, not the error itself


def test_predeclared_with_lacks_marker_explanation() -> None:
    """Same gap as the for-loop case, for `with`-statement pre-declared targets."""
    result = run_internal_ty(PREDECLARED_WITH)

    assert result.returncode != 0
    assert "is not assignable to `Mut[StringIO]`" in result.stdout
    assert MUT_MARKER_EXPLANATION not in result.stdout
    assert "StringIO & MutMarker" in result.stdout  # from reveal_type, not the error itself


def test_predeclared_unpacking_has_marker_explanation() -> None:
    """Unlike for-loop/with, unpacking's message shape matches plain assignment."""
    result = run_internal_ty(PREDECLARED_UNPACKING)

    assert result.returncode != 0
    assert MUT_MARKER_EXPLANATION in result.stdout
    assert "int & MutMarker" in result.stdout


def test_container_mutability_is_compositional() -> None:
    """`Mut[list[User]]` grants container-only permission (plain elements accepted);
    `Mut[list[Mut[User]]]` additionally grants element-mutation permission (`Mut`
    elements accepted too). Both driven by real stdlib `list.append`, no custom
    stdlib stubs needed for this distinction.
    """
    result = run_internal_ty(CONTAINER_MUTABILITY_OK)

    assert result.returncode == 0, result.stdout + result.stderr


def test_container_mutability_rejects_plain_element_for_deeply_mut_list() -> None:
    """`Mut[list[Mut[User]]]` must reject a plain `User` element -- it's missing the
    element-level `MutMarker` that `Mut[list[User]]` alone would not have required.
    """
    result = run_internal_ty(CONTAINER_MUTABILITY_BAD)

    assert result.returncode != 0
    assert MUT_MARKER_EXPLANATION in result.stdout
    assert "User & MutMarker" in result.stdout


def test_protocol_conformance_catches_mut_mismatch() -> None:
    """A class with a plain field must fail to satisfy a Protocol declaring that
    field as `Mut` -- `ty`'s native structural conformance checking catches this
    with zero custom logic, per CLAUDE.md's "resolved by the intersection-type
    approach" note in the Protocols section.
    """
    result = run_internal_ty(PROTOCOL_CONFORMANCE_BAD)

    assert result.returncode != 0
    assert "not assignable to protocol `HasValue`" in result.stdout
    assert "protocol member `value` is incompatible" in result.stdout
