"""`mut_check.check`'s `untyped` mode: CLAUDE.md's "Untyped-code handling" `Open` item.

`ty` itself has no equivalent -- confirmed directly (`ty check --help`
exposes no strict/untyped-body flag at all, gradual typing is unconditional
there). This is `mut_check`'s own knob, and only governs its own custom
pass (`_reassignment`), per `mut_check.check`'s docstring.
"""

from _checkers import FIXTURES_DIR, diagnostics_text, is_clean

from mut_check import check

NO_MUT_IN_SCOPE = FIXTURES_DIR / "mut_check_untyped_ratchet_no_mut_in_scope.py"
FULLY_UNTYPED = FIXTURES_DIR / "mut_check_untyped_fully_untyped_module.py"

CODE = "reassignment-without-mut"


def test_permissive_is_the_default_and_skips_a_scope_with_no_mut() -> None:
    diagnostics = check(NO_MUT_IN_SCOPE)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_permissive_explicit_matches_the_default() -> None:
    diagnostics = check(NO_MUT_IN_SCOPE, untyped="permissive")

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_strict_disables_the_ratchet_and_flags_the_scope() -> None:
    diagnostics = check(NO_MUT_IN_SCOPE, untyped="strict")

    assert not is_clean(diagnostics)
    assert any(d.code == CODE for d in diagnostics)


def test_permissive_skips_a_fully_untyped_module() -> None:
    diagnostics = check(FULLY_UNTYPED)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_ignored_also_skips_a_fully_untyped_module() -> None:
    """`"ignored"` and `"permissive"` report identically here -- see the
    fixture's docstring for why that's expected, not a bug.
    """
    diagnostics = check(FULLY_UNTYPED, untyped="ignored")

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_strict_flags_the_fully_untyped_module_too() -> None:
    diagnostics = check(FULLY_UNTYPED, untyped="strict")

    assert not is_clean(diagnostics)
    assert any(d.code == CODE for d in diagnostics)
