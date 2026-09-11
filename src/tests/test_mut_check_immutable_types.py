"""`mut_check`'s diagnostic filter must suppress the immutable-type aliasing false positive.

Per CLAUDE.md's "Immutable types always satisfy `Mut[T]`, aliased or not": a
value of an immutable type satisfies a `Mut[T]` position unconditionally,
whether freshly constructed or an aliased reference from anywhere -- there's
no mutation hazard for a type nothing can be mutated through. This
supersedes the general aliasing rejection for immutable types specifically;
contrast with test_mut_check.py's test_aliased_plain_t_is_rejected_for_mut_position,
which uses `list[int]` (genuinely mutable) and must remain rejected. It's
also a separate exemption from the construction/literal one in
test_mut_check_filter.py -- driven by the *type* being immutable, not by the
value being freshly constructed.

Per CLAUDE.md's "Generalizes to read-only abstract types": the exemption
isn't limited to the fixed concrete-type list -- it covers any type with no
mutating members in its own definition, which also includes structural
types like `Sequence`/`Mapping` (but not their `Mutable*` counterparts).
"""

from _checkers import FIXTURES_DIR, diagnostics_text, is_clean

from mut_check import check

ALIASED_ASSIGNMENT_INT = FIXTURES_DIR / "mut_check_immutable_aliased_assignment_int.py"
ALIASED_ASSIGNMENT_STR = FIXTURES_DIR / "mut_check_immutable_aliased_assignment_str.py"
ALIASED_ARGUMENT_INT = FIXTURES_DIR / "mut_check_immutable_aliased_argument.py"
TUPLE_OF_IMMUTABLES = FIXTURES_DIR / "mut_check_immutable_tuple_of_immutables.py"
TUPLE_WITH_MUTABLE_ELEMENT = FIXTURES_DIR / "mut_check_immutable_tuple_with_mutable_element.py"
ABSTRACT_SEQUENCE = FIXTURES_DIR / "mut_check_immutable_abstract_sequence.py"
ABSTRACT_MAPPING = FIXTURES_DIR / "mut_check_immutable_abstract_mapping.py"
MUTABLE_SEQUENCE_STILL_REJECTED = FIXTURES_DIR / "mut_check_mutable_sequence_still_rejected.py"


def test_aliased_int_satisfies_mut_via_assignment() -> None:
    diagnostics = check(ALIASED_ASSIGNMENT_INT)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_aliased_str_satisfies_mut_via_assignment() -> None:
    diagnostics = check(ALIASED_ASSIGNMENT_STR)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_aliased_int_satisfies_mut_via_argument() -> None:
    """Argument-passing produces a different diagnostic code and message shape
    (`invalid-argument-type`) than plain assignment (`invalid-assignment`) --
    the exemption must apply to both.
    """
    diagnostics = check(ALIASED_ARGUMENT_INT)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_tuple_of_immutables_satisfies_mut() -> None:
    diagnostics = check(TUPLE_OF_IMMUTABLES)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_tuple_is_exempt_regardless_of_element_mutability() -> None:
    """A tuple has no mutating operations at all, so it's exempt even when one
    of its elements is a mutable type -- aliasing the tuple binding can never
    expose a way to restructure it. Mutating the element itself is a separate
    concern governed by that element's own `Mut` annotation.
    """
    diagnostics = check(TUPLE_WITH_MUTABLE_ELEMENT)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_abstract_sequence_satisfies_mut() -> None:
    """`Sequence[T]` has no mutating members in its own definition -- the
    exemption isn't limited to the fixed concrete-type list.
    """
    diagnostics = check(ABSTRACT_SEQUENCE)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_abstract_mapping_satisfies_mut() -> None:
    diagnostics = check(ABSTRACT_MAPPING)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_mutable_sequence_is_not_exempt() -> None:
    """Control case: `MutableSequence` declares mutating members, unlike
    `Sequence` -- the exemption must not overreach to it.
    """
    diagnostics = check(MUTABLE_SEQUENCE_STILL_REJECTED)

    assert not is_clean(diagnostics)
    assert "not assignable to `Mut[MutableSequence[int]]`" in diagnostics_text(diagnostics)
