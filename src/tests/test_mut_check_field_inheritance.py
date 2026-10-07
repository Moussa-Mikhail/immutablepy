"""Fields inherit mutability from their owner (docs/decisions.md's "Fields inherit
mutability from the owner").

Implemented in the private `ty` backend, not in a custom pass: `MutMarker`'s
`__getattr__` (stubs/internal/immutablepy/__init__.pyi) makes `o.field` resolve
to `declared & MutMarker` through a `Mut` owner and to plain `declared` through a
plain one, so `ty`'s native `Mut` checks on the *receiver* of a mutating call do
the rest. The field itself is declared plain.

An outer `Mut` on a field annotation is the escape hatch: that field is mutable
through any owner, plain included (interior state like a memo). Initializing it
with a fresh value is accepted; handing it a plain reference is not.

What this does not cover: attribute *writes* through a plain owner (`p.field = v`)
-- `ty` checks those against the declared type, so they go unreported -- and a
typo'd attribute name on a `Mut` owner (`__getattr__` makes every name resolve; the
plain checkers still report it).
"""

from _checkers import FIXTURES_DIR, diagnostics_text, is_clean

from mut_check import check

MUT_OWNER_OK = FIXTURES_DIR / "mut_check_field_inherit_mut_owner_ok.py"
PLAIN_OWNER_BAD = FIXTURES_DIR / "mut_check_field_inherit_plain_owner_bad.py"
METHOD_CALLS_BAD = FIXTURES_DIR / "mut_check_field_inherit_method_calls_bad.py"
HATCH_OK = FIXTURES_DIR / "mut_check_field_hatch_ok.py"
HATCH_PLAIN_REF_BAD = FIXTURES_DIR / "mut_check_field_hatch_plain_ref_bad.py"

ARGUMENT_CODE = "invalid-argument-type"
ASSIGNMENT_CODE = "invalid-assignment"


def test_mutating_a_field_through_a_mut_owner_is_permitted() -> None:
    """Direct, via `self` in a `Mut[Self]` method, through an attribute chain, and
    correct calls to instance/static/class methods -- all clean.
    """
    diagnostics = check(MUT_OWNER_OK)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_mutating_a_field_through_a_plain_owner_is_rejected() -> None:
    """The same mutations through a plain owner: plain `self`, a plain parameter,
    and a chain rooted at a plain parameter -- exactly these three.
    """
    diagnostics = check(PLAIN_OWNER_BAD)

    assert [d.code for d in diagnostics] == [ARGUMENT_CODE] * 3
    assert [d.line for d in diagnostics] == [15, 24, 28]
    assert "Mut[" in diagnostics_text(diagnostics)


def test_method_calls_through_a_mut_owner_are_still_checked() -> None:
    """Wrong-argument calls through a `Mut` owner are still reported for instance,
    static and class methods. A `__getattr__` that collapsed methods to `Never`
    would make all three silently disappear.
    """
    diagnostics = check(METHOD_CALLS_BAD)

    assert [d.code for d in diagnostics] == [ARGUMENT_CODE] * 3
    assert [d.line for d in diagnostics] == [26, 27, 28]


def test_mut_annotated_field_is_mutable_through_any_owner() -> None:
    """The escape hatch: a plain-`self` method and a plain parameter both mutate a
    `Mut`-annotated field, and both initialization forms (`self.x = {}` and
    `self.x: Mut[...] = []`) are accepted -- the attribute target, not the value,
    is where `ty` points.
    """
    diagnostics = check(HATCH_OK)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_mut_annotated_field_rejects_a_plain_reference() -> None:
    """Control: a plain (read-only) reference can't be stored in an always-mutable
    field, in a constructor or through another object -- exactly these two.
    """
    diagnostics = check(HATCH_PLAIN_REF_BAD)

    assert [d.code for d in diagnostics] == [ASSIGNMENT_CODE] * 2
    assert [d.line for d in diagnostics] == [16, 20]
