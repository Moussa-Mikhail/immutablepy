"""`mut_check` must actually gate `Mut[T]`.

Unlike the compatibility tests, these go through `mut_check.check` -- the
app's own entry point -- rather than the plain public alias real checkers
see. If any of these stopped holding, `Mut[T] <: T` enforcement would be
silently doing nothing. `check` now includes the construction/literal
diagnostic filter (see test_mut_check_filter.py); the tests here document
the diagnostic shapes that filter must -- and must not -- touch, alongside
guarantees the underlying checker enforces natively.
"""

from _checkers import FIXTURES_DIR, diagnostics_text, is_clean

from mut_check import check

REJECTS_ALIASED_T = FIXTURES_DIR / "mut_check_rejects_aliased_t.py"
ACCEPTS_MUT_WHERE_T_EXPECTED = FIXTURES_DIR / "mut_check_accepts_mut_where_t_expected.py"
GENERIC_SUBSTITUTION = FIXTURES_DIR / "mut_check_generic_substitution.py"
PREDECLARED_FOR_LOOP = FIXTURES_DIR / "mut_check_predeclared_for_loop.py"
FOR_LOOP_READ_ONLY = FIXTURES_DIR / "mut_check_for_loop_read_only_needs_no_mut.py"
FOR_LOOP_MUTABLE_TYPE_READ_ONLY = FIXTURES_DIR / "mut_check_for_loop_mutable_type_read_only.py"
WITH_READ_ONLY = FIXTURES_DIR / "mut_check_with_read_only.py"
UNPACKING_WITHOUT_MUT = FIXTURES_DIR / "mut_check_unpacking_without_mut.py"
PREDECLARED_UNPACKING_MUTABLE = FIXTURES_DIR / "mut_check_predeclared_unpacking_mutable.py"
CONTAINER_MUTABILITY_OK = FIXTURES_DIR / "mut_check_container_mutability_ok.py"
CONTAINER_MUTABILITY_BAD = FIXTURES_DIR / "mut_check_container_mutability_bad.py"
SELF_REQUIRES_MUT_OK = FIXTURES_DIR / "mut_check_self_requires_mut_ok.py"
SELF_REQUIRES_MUT_BAD = FIXTURES_DIR / "mut_check_self_requires_mut_bad.py"

MUT_MARKER_EXPLANATION = "not assignable to element `MutMarker`"


def test_plain_t_is_rejected_for_mut_position() -> None:
    """`T` here is a mutable type (`list[int]`) -- `Mut[T]` and `T` genuinely
    differ in what they permit for mutable types, unlike immutable ones (see
    CLAUDE.md's "Immutable types always satisfy Mut[T]").
    """
    diagnostics = check(REJECTS_ALIASED_T)

    assert not is_clean(diagnostics)
    assert "MutMarker" in diagnostics_text(diagnostics)


def test_mut_is_accepted_where_plain_t_expected() -> None:
    """The forward direction of `Mut[T] <: T`: no filter is needed for this side."""
    diagnostics = check(ACCEPTS_MUT_WHERE_T_EXPECTED)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_intersection_survives_generic_substitution() -> None:
    """`Container[int].item` (declared `Mut[T]`) must reveal `int & MutMarker`, not `int`."""
    diagnostics = check(GENERIC_SUBSTITUTION)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)
    assert "int & MutMarker" in diagnostics_text(diagnostics)


def test_for_loop_reading_only_needs_no_mut() -> None:
    """Control case: a for-loop that only reads its target needs no `Mut[T]`
    pre-declaration at all -- each iteration's binding is effectively fresh,
    like the construction exemption, not a reassignment needing permission.
    """
    diagnostics = check(FOR_LOOP_READ_ONLY)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_predeclared_for_loop_with_immutable_type_is_clean() -> None:
    """Pre-declaring `Mut[int]` is only justified here because the loop body
    reassigns `i` (`i += 1`) -- see test_for_loop_reading_only_needs_no_mut for
    the case where it isn't needed. `check()` must come back clean: the
    target-binding diagnostic is exempt per `filter_construction_exemption`,
    and the augmented-assignment one is exempt per `filter_immutable_type_exemption`
    (int is immutable).
    """
    diagnostics = check(PREDECLARED_FOR_LOOP)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_for_loop_mutable_type_read_only_needs_no_mut() -> None:
    """Same as test_for_loop_reading_only_needs_no_mut, but with a genuinely
    mutable type (`Box`) instead of `int` -- confirms "read-only needs no `Mut`"
    doesn't depend on the target's type. `reveal_type` shows plain `Box`, not
    `Box & MutMarker`.
    """
    diagnostics = check(FOR_LOOP_MUTABLE_TYPE_READ_ONLY)
    text = diagnostics_text(diagnostics)

    assert is_clean(diagnostics), text
    assert "MutMarker" not in text


def test_with_read_only_needs_no_mut() -> None:
    """A `with`-statement target that's only read needs no `Mut` pre-declaration
    at all, same as for-loops. `reveal_type` shows plain `StringIO`, not
    `StringIO & MutMarker`.
    """
    diagnostics = check(WITH_READ_ONLY)
    text = diagnostics_text(diagnostics)

    assert is_clean(diagnostics), text
    assert "MutMarker" not in text


def test_unpacking_without_mut_needs_no_mut() -> None:
    """Per CLAUDE.md: "Unpacking without pre-declaration produces immutable
    bindings by default." No `Mut` pre-declaration needed when the unpacked
    targets are only read afterward (see
    test_predeclared_unpacking_mutable_type_is_rejected for the case where
    a *mutable* unpacked value's already-committed plain type is still
    correctly rejected).
    """
    diagnostics = check(UNPACKING_WITHOUT_MUT)
    text = diagnostics_text(diagnostics)

    assert is_clean(diagnostics), text
    assert "MutMarker" not in text


def test_predeclared_unpacking_mutable_type_is_rejected() -> None:
    """Same shape as above, but `list[int]` isn't on the immutable allowlist, so
    its already-committed plain type via unpacking is still correctly rejected.
    """
    diagnostics = check(PREDECLARED_UNPACKING_MUTABLE)
    text = diagnostics_text(diagnostics)

    assert not is_clean(diagnostics)
    assert MUT_MARKER_EXPLANATION in text
    assert "list[int] & MutMarker" in text


def test_container_mutability_is_compositional() -> None:
    """`Mut[list[User]]` grants container-only permission (plain elements accepted);
    `Mut[list[Mut[User]]]` additionally grants element-mutation permission (`Mut`
    elements accepted too). Both driven by real stdlib `list.append`, no custom
    stdlib stubs needed for this distinction.
    """
    diagnostics = check(CONTAINER_MUTABILITY_OK)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_container_mutability_rejects_plain_element_for_deeply_mut_list() -> None:
    """`Mut[list[Mut[User]]]` must reject a plain `User` element -- it's missing the
    element-level `MutMarker` that `Mut[list[User]]` alone would not have required.
    """
    diagnostics = check(CONTAINER_MUTABILITY_BAD)
    text = diagnostics_text(diagnostics)

    assert not is_clean(diagnostics)
    assert MUT_MARKER_EXPLANATION in text
    assert "User & MutMarker" in text


def test_self_requires_mut_is_accepted_on_mut_receiver() -> None:
    """Control case: a `self: Mut[Self]` method called on a `Mut[...]` receiver
    must be accepted -- the receiver carries `MutMarker`.
    """
    diagnostics = check(SELF_REQUIRES_MUT_OK)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_self_requires_mut_is_rejected_on_plain_receiver() -> None:
    """A method declared `self: Mut[Self]` must reject being called on a plain
    (non-`Mut`) receiver -- this is what makes `Mut[Self]` actually gate mutating
    methods, not just document them.
    """
    diagnostics = check(SELF_REQUIRES_MUT_BAD)
    text = diagnostics_text(diagnostics)

    assert not is_clean(diagnostics)
    assert MUT_MARKER_EXPLANATION in text
    assert "Counter & MutMarker" in text
