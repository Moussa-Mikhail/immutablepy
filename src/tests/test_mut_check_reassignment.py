"""`mut_check._reassignment` must catch reassigning a plain (non-`Mut`) local.

`ty` has no notion of this at all -- confirmed directly, none of the
"without_mut" fixtures below produce anything from `ty` itself. These
diagnostics come entirely from `mut_check`'s own custom check, the first
piece of the not-yet-built custom pass (per CLAUDE.md's "Open" items).
"""

from _checkers import FIXTURES_DIR, diagnostics_text, is_clean

from mut_check import check

LOOP_VAR_WITHOUT_MUT = FIXTURES_DIR / "mut_check_reassignment_loop_var_without_mut.py"
LOOP_VAR_WITH_MUT = FIXTURES_DIR / "mut_check_reassignment_loop_var_with_mut.py"
PLAIN_LOCAL = FIXTURES_DIR / "mut_check_reassignment_plain_local.py"
PARAMETER_WITHOUT_MUT = FIXTURES_DIR / "mut_check_reassignment_parameter.py"
PARAMETER_WITH_MUT = FIXTURES_DIR / "mut_check_reassignment_parameter_with_mut.py"
BARE_DECLARATION_THEN_UNPACKING = FIXTURES_DIR / "mut_check_reassignment_bare_declaration_then_unpacking.py"
NESTED_SCOPE_ISOLATED = FIXTURES_DIR / "mut_check_reassignment_nested_scope_isolated.py"
COMPREHENSION_EXEMPT = FIXTURES_DIR / "mut_check_reassignment_comprehension_exempt.py"

CODE = "reassignment-without-mut"


def test_loop_var_mutated_without_mut_is_rejected() -> None:
    diagnostics = check(LOOP_VAR_WITHOUT_MUT)

    assert not is_clean(diagnostics)
    assert any(d.code == CODE for d in diagnostics)


def test_loop_var_mutated_with_mut_is_permitted() -> None:
    diagnostics = check(LOOP_VAR_WITH_MUT)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_plain_local_second_assignment_is_rejected() -> None:
    """The first assignment is free; only the second one is flagged."""
    diagnostics = check(PLAIN_LOCAL)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == CODE
    assert diagnostics[0].line == 7  # the second `x = ...`, not the first


def test_parameter_reassignment_without_mut_is_rejected() -> None:
    """Unlike a fresh local, a parameter is already bound at function entry --
    even the first body reassignment is a violation.
    """
    diagnostics = check(PARAMETER_WITHOUT_MUT)

    assert not is_clean(diagnostics)
    assert any(d.code == CODE for d in diagnostics)


def test_parameter_reassignment_with_mut_is_permitted() -> None:
    diagnostics = check(PARAMETER_WITH_MUT)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_bare_declaration_then_unpacking_is_not_a_false_positive() -> None:
    """Regression: a bare `AnnAssign` (no value) must not consume the free
    first assignment for the name it declares.
    """
    diagnostics = check(BARE_DECLARATION_THEN_UNPACKING)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_nested_scope_is_isolated_but_still_checked() -> None:
    """The inner function's own second assignment is a real violation, but it
    must not be confused with (or leak into) the outer scope's `x`.
    """
    diagnostics = check(NESTED_SCOPE_ISOLATED)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == CODE
    assert diagnostics[0].line == 13  # inner's `x = 3`, not outer's `x = 1` or inner's `x = 2`


def test_comprehension_variable_is_exempt() -> None:
    diagnostics = check(COMPREHENSION_EXEMPT)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)
