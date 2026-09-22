"""`mut_check` must gate the stdlib mutable containers' own mutating methods.

Distinct from test_mut_check.py's test_container_mutability_* (which fix the
receiver as already `Mut[...]` and test *element*-type compositionality
instead): these pin that the vendored typeshed fork's stubs
(`stubs/typeshed/stdlib/builtins.pyi`/`typing.pyi`) actually require a
`Mut[...]` receiver in the first place, for `list`/`dict`/`set`/`bytearray`'s
own mutating methods and for the ones each inherits un-overridden from its
`Mutable*` mixin. This is exactly the ground truth a future typeshed sync or
stub edit could silently regress -- see docs/decisions.md's "Stdlib and
third-party support" and the confirmed `ty` bug (`Self` inside `Intersection`
failing to substitute) the `Mut[S]`/bound-`TypeVar` pattern throughout those
stubs works around.
"""

from _checkers import FIXTURES_DIR, diagnostics_text, is_clean

from mut_check import check

CONTAINER_MUTATION_OK = FIXTURES_DIR / "mut_check_stdlib_container_mutation_ok.py"
CONTAINER_MUTATION_BAD = FIXTURES_DIR / "mut_check_stdlib_container_mutation_bad.py"

# One call per mutating method exercised in the fixtures -- list, dict, set,
# bytearray respectively. Asserted as an exact count, not just `not
# is_clean`, so a partial regression (one type/method silently starting to
# pass again while the rest still fail) can't hide behind the others.
_EXPECTED_REJECTION_COUNT = 10 + 8 + 13 + 11


def test_stdlib_container_mutation_is_accepted_on_mut_receiver() -> None:
    """Control case: every mutating method call in the fixture has a
    `Mut[...]`-typed receiver and must be accepted with zero diagnostics.
    """
    diagnostics = check(CONTAINER_MUTATION_OK)

    assert is_clean(diagnostics), diagnostics_text(diagnostics)


def test_stdlib_container_mutation_is_rejected_on_plain_receiver() -> None:
    """The same calls, method for method, on a plain (non-`Mut`) receiver --
    every single one must be rejected. This is what makes the stdlib stubs'
    `Mut[S]` receivers actually gate mutation, not just document it.
    """
    diagnostics = check(CONTAINER_MUTATION_BAD)

    assert not is_clean(diagnostics)
    assert len(diagnostics) == _EXPECTED_REJECTION_COUNT, diagnostics_text(diagnostics)
