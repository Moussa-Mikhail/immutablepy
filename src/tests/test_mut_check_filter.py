# noinspection GrazieStyle
"""`mut_check`'s diagnostic filter must suppress the construction/literal false positive.

Per CLAUDE.md's construction exemption, an object created in the current
scope can be assigned/passed/returned as `Mut` -- it's provably unaliased at
that point. A fresh literal/constructor call/comprehension in a `Mut[T]`
position must type-check clean through `mut_check` -- even though the
underlying checker rejects it for lacking `MutMarker` (see test_mut_check.py's
`test_aliased_plain_t_is_rejected_for_mut_position` for a true positive the
filter must never touch).

Per `mut_check._filter`, this applies uniformly to assignment, `return`
values, and call arguments (`ty` always points its diagnostic at the fresh
expression's own position, regardless of syntactic role) -- but not to
method calls (`obj.method(...)`; the call's position coincides with the
*receiver*'s, not a fresh return value -- see
test_mut_check.py's `test_self_requires_mut_is_rejected_on_plain_receiver`),
and not to `Mut[` mentions nested under a `└──` structural-mismatch tree
(see `test_protocol_conformance_catches_mut_mismatch`) -- both confirmed as
real overreach bugs while building this.
"""

from _checkers import FIXTURES_DIR, diagnostics_text, is_clean

from mut_check import check

INT_LITERAL = FIXTURES_DIR / "mut_check_filter_int_literal.py"
STR_LITERAL = FIXTURES_DIR / "mut_check_filter_str_literal.py"
LIST_LITERAL = FIXTURES_DIR / "mut_check_filter_list_literal.py"
DICT_LITERAL = FIXTURES_DIR / "mut_check_filter_dict_literal.py"
SET_LITERAL = FIXTURES_DIR / "mut_check_filter_set_literal.py"
REJECTS_ALIASED_ASSIGNMENT = FIXTURES_DIR / "mut_check_filter_rejects_aliased_assignment.py"
FRESH_RETURN_VALUE = FIXTURES_DIR / "mut_check_filter_fresh_return_value.py"
FRESH_CALL_ARGUMENT = FIXTURES_DIR / "mut_check_filter_fresh_call_argument.py"
BUILTIN_CONSTRUCTOR = FIXTURES_DIR / "mut_check_filter_builtin_constructor.py"
FUNCTION_CALL_NOT_EXEMPT = FIXTURES_DIR / "mut_check_filter_function_call_not_exempt.py"


def test_int_literal_satisfies_mut() -> None:
    diagnostics = check(INT_LITERAL)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_str_literal_satisfies_mut() -> None:
    diagnostics = check(STR_LITERAL)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_list_literal_satisfies_mut() -> None:
    diagnostics = check(LIST_LITERAL)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_dict_literal_satisfies_mut() -> None:
    diagnostics = check(DICT_LITERAL)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_set_literal_satisfies_mut() -> None:
    diagnostics = check(SET_LITERAL)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_fresh_return_value_satisfies_mut() -> None:
    diagnostics = check(FRESH_RETURN_VALUE)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_fresh_call_argument_satisfies_mut() -> None:
    diagnostics = check(FRESH_CALL_ARGUMENT)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_builtin_mutable_constructor_satisfies_mut() -> None:
    diagnostics = check(BUILTIN_CONSTRUCTOR)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_ordinary_function_call_is_not_exempt() -> None:
    """Regression: a bare-name call is only fresh if it's a class instantiation
    or a built-in mutable-container constructor -- not just any callable. An
    earlier version inferred freshness from `get_list`'s body instead of its
    declared (plain) return type.
    """
    diagnostics = check(FUNCTION_CALL_NOT_EXEMPT)

    assert not is_clean(diagnostics)
    assert "not assignable to `Mut[list[int]]`" in diagnostics_text(diagnostics)


def test_aliased_assignment_is_not_suppressed() -> None:
    """Same `AnnAssign` shape as the literal fixtures, but a plain variable
    reference, not a literal -- the filter must not overreach and suppress this.
    Uses `list[int]` (mutable) so this remains a true positive under the
    immutable-type exemption too -- see test_mut_check_immutable_types.py.
    """
    diagnostics = check(REJECTS_ALIASED_ASSIGNMENT)

    assert not is_clean(diagnostics)
    assert "not assignable to `Mut[list[int]]`" in diagnostics_text(diagnostics)
