"""`mut_check`'s diagnostic filter must suppress the construction/literal false positive.

Per CLAUDE.md's construction exemption ("Constructors and literals satisfy
`Mut` positions"), a fresh literal assigned directly to a `Mut[T]`-declared
binding is provably unaliased and must type-check clean through
`mut_check` -- even though the underlying checker rejects it for lacking
`MutMarker` (see test_mut_check.py's `test_aliased_plain_t_is_rejected_for_mut_position`
for a true positive the filter must never touch).

Scoped deliberately narrow, per `mut_check._filter`: only `AnnAssign` with a
literal display value (`ast.Constant`/`List`/`Dict`/`Set`/`Tuple`), not
constructor calls, for-loop/`with` targets, or unpacking.
"""

from _checkers import FIXTURES_DIR, diagnostics_text, is_clean

from mut_check import check

INT_LITERAL = FIXTURES_DIR / "mut_check_filter_int_literal.py"
STR_LITERAL = FIXTURES_DIR / "mut_check_filter_str_literal.py"
LIST_LITERAL = FIXTURES_DIR / "mut_check_filter_list_literal.py"
DICT_LITERAL = FIXTURES_DIR / "mut_check_filter_dict_literal.py"
SET_LITERAL = FIXTURES_DIR / "mut_check_filter_set_literal.py"
REJECTS_ALIASED_ASSIGNMENT = FIXTURES_DIR / "mut_check_filter_rejects_aliased_assignment.py"


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


def test_aliased_assignment_is_not_suppressed() -> None:
    """Same `AnnAssign` shape as the literal fixtures, but a plain variable
    reference, not a literal -- the filter must not overreach and suppress this.
    """
    diagnostics = check(REJECTS_ALIASED_ASSIGNMENT)

    assert not is_clean(diagnostics)
    assert "not assignable to `Mut[int]`" in diagnostics_text(diagnostics)
