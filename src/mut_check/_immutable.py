"""
Suppress `ty`'s immutable-type false positive.

Per CLAUDE.md's "Immutable types always satisfy `Mut[T]`": a value of a type
with no mutating members in its own definition (`int`, `tuple`, `Sequence`,
...) must satisfy a `Mut[T]` position unconditionally, regardless of where
it came from -- a fresh literal or a `Name` pointing to an existing binding,
it makes no difference. This isn't about aliasing (`Mut` tracks per-binding
permission, not object uniqueness -- see `_filter`'s docstring); it's that
for a type with zero mutating operations, `Mut[T]` and `T` grant exactly the
same set of possible operations. There's no permission gap for `Mut[T]` to
protect in the first place, so the `MutMarker` mismatch `ty` reports for
these types is a structural artifact of the intersection encoding (which has
no way to see "this type has no mutating members at all"), not a meaningful
constraint. This module corrects that after the fact.

Unlike `_filter.filter_construction_exemption` (which cares whether a value
has a prior type commitment, and so must inspect the source AST), this
exemption doesn't care how the value was produced or where it came from --
only its type. So instead of AST analysis, this reads the type straight out
of `ty`'s own diagnostic. Most of the time that's the info line naming the
source type as
not assignable to element `MutMarker` (e.g. "type `int` is not assignable to
element `MutMarker` of intersection `int & MutMarker`").

Matched against an ANSI-stripped copy of the text -- `ty` is invoked with
`--color=always` (per `_ansi`'s docstring), and its color codes land inside
the literal message (e.g. between `info` and `:`), not just around it.

Per CLAUDE.md's "Hybrid enforcement" note, for-loop/`with` pre-declared targets -- and, as it
turns out, augmented assignment (`total += i`) -- raise the same
`invalid-assignment` code without that info line at all (confirmed: `total:
Mut[int] = 0; total += i` inside a loop produces "Object of type `int` is
not assignable to `Mut[int]`" with no info line whatsoever). The primary
message is always present regardless, so it's the fallback: "Object of type
`X` is not assignable to `Mut[...]`" (optionally "...to attribute `name` of
type `Mut[...]`" for attributes). Either way the extracted name is compared
against the hand-maintained immutable-type allowlist below (generic
parameters stripped, so `tuple[list[int], int]` and `Sequence[int]` are
recognized as `tuple` and `Sequence`).

Scoped to `invalid-assignment` and `invalid-argument-type` -- the two
diagnostic codes this exemption is known to matter for.
"""

import re

from immutablepy import Mut
from mut_check._ansi import strip_ansi
from mut_check._diagnostics import Diagnostic

_MUT_MARKER_TYPE = re.compile(r"info: type `(?P<type>[^`]+)` is not assignable to element `MutMarker`")
_PRIMARY_MESSAGE_TYPE = re.compile(
    r"Object of type `(?P<type>[^`]+)` is not assignable to (?:attribute `\w+` of type )?`Mut\[",
)

_EXEMPT_CODES = frozenset({"invalid-assignment", "invalid-argument-type"})

_IMMUTABLE_TYPE_NAMES = frozenset(
    {
        # `ty` infers literal expressions as `Literal[1]`/`Literal["x"]`/etc, not
        # their concrete type -- but per PEP 586, `Literal` only ever holds int,
        # str, bytes, bool, or an enum member, all immutable regardless of which.
        "Literal",
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
    }
)


def _base_type_name(type_text: str) -> str:
    """Strip generic parameters: `tuple[list[int], int]` -> `tuple`."""
    return type_text.split("[", 1)[0]


def _is_immutable_type_false_positive(diagnostic: Diagnostic) -> bool:
    if diagnostic.code not in _EXEMPT_CODES:
        return False
    text = strip_ansi(diagnostic.text)
    match = _MUT_MARKER_TYPE.search(text) or _PRIMARY_MESSAGE_TYPE.search(text)
    return match is not None and _base_type_name(match["type"]) in _IMMUTABLE_TYPE_NAMES


def filter_immutable_type_exemption(diagnostics: list[Diagnostic]) -> Mut[list[Diagnostic]]:
    """Drop diagnostics that are exactly `ty`'s immutable-type false positive."""
    return [d for d in diagnostics if not _is_immutable_type_false_positive(d)]
