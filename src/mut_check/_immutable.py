"""
Suppress `ty`'s immutable-type aliasing false positive.

Per CLAUDE.md's "Immutable types always satisfy `Mut[T]`, aliased or not": a
value of a type with no mutating members in its own definition (`int`,
`tuple`, `Sequence`, ...) must satisfy a `Mut[T]` position unconditionally --
fresh or aliased, it doesn't matter, since nothing can mutate it through any
reference. `ty` has no notion of this exemption, so it rejects the aliased
case the same as a genuinely mutable one; this module corrects that after
the fact.

Unlike `_filter.filter_construction_exemption` (which must inspect the
source AST to tell a fresh literal from an aliased reference), this
exemption doesn't care how the value was produced -- only its type. So
instead of AST analysis, this reads the type straight out of `ty`'s own
diagnostic. Most of the time that's the info line naming the source type as
not assignable to element `MutMarker` (e.g. "type `int` is not assignable to
element `MutMarker` of intersection `int & MutMarker`"). But per CLAUDE.md's
"Hybrid enforcement" note, for-loop/`with` pre-declared targets -- and, as it
turns out, augmented assignment (`total += i`) -- raise the same
`invalid-assignment` code without that info line at all (confirmed: `total:
Mut[int] = 0; total += i` inside a loop produces "Object of type `int` is
not assignable to `Mut[int]`" with no info line whatsoever). The primary
message is always present regardless, so it's the fallback: "Object of type
`X` is not assignable to `Mut[...`" (optionally "...to attribute `name` of
type `Mut[...`" for attributes). Either way the extracted name is compared
against the hand-maintained immutable-type allowlist below (generic
parameters stripped, so `tuple[list[int], int]` and `Sequence[int]` are
recognized as `tuple` and `Sequence`).

Scoped to `invalid-assignment` and `invalid-argument-type` -- the two
diagnostic codes this exemption is known to matter for.
"""

import re

from mut_check._diagnostics import Diagnostic

_MUT_MARKER_TYPE = re.compile(r"info: type `(?P<type>[^`]+)` is not assignable to element `MutMarker`")
_PRIMARY_MESSAGE_TYPE = re.compile(
    r"Object of type `(?P<type>[^`]+)` is not assignable to (?:attribute `\w+` of type )?`Mut\[",
)

_EXEMPT_CODES = frozenset({"invalid-assignment", "invalid-argument-type"})

_IMMUTABLE_TYPE_NAMES = frozenset({
    # Concrete: no mutating operations exist on these types, regardless of
    # what a generic parameter (e.g. tuple's elements) holds.
    "int",
    "str",
    "bytes",
    "float",
    "bool",
    "complex",
    "frozenset",
    "tuple",
    # Read-only abstract types: no mutating members in their own definition.
    # Their `Mutable*` counterparts (MutableSequence, MutableMapping,
    # MutableSet) are deliberately absent -- those do declare them.
    "Sequence",
    "Mapping",
    "Collection",
    "Iterable",
    "Iterator",
    "Container",
    "Sized",
    "Hashable",
    "Reversible",
    "KeysView",
    "ValuesView",
    "ItemsView",
})


def _base_type_name(type_text: str) -> str:
    """Strip generic parameters: `tuple[list[int], int]` -> `tuple`."""
    return type_text.split("[", 1)[0]


def _is_immutable_type_false_positive(diagnostic: Diagnostic) -> bool:
    if diagnostic.code not in _EXEMPT_CODES:
        return False
    match = _MUT_MARKER_TYPE.search(diagnostic.text) or _PRIMARY_MESSAGE_TYPE.search(diagnostic.text)
    return match is not None and _base_type_name(match["type"]) in _IMMUTABLE_TYPE_NAMES


def filter_immutable_type_exemption(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    """Drop diagnostics that are exactly `ty`'s immutable-type aliasing false positive."""
    return [d for d in diagnostics if not _is_immutable_type_false_positive(d)]
