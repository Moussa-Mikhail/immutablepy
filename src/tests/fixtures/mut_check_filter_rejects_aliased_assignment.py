"""Control case: the filter must not overreach.

Same `AnnAssign` shape as the literal fixtures (`x: Mut[T] = <value>`), but
the value is a plain variable reference, not a literal display -- `y`'s
type is already committed as plain `list[int]` by its own declaration, so
the filter's AST check must tell these apart and leave this one rejected.
Uses `list[int]` (a genuinely mutable type) rather than `int`, so this
remains a true positive under the immutable-type exemption too (see
test_mut_check_immutable_types.py) -- for a mutable type, `Mut[T]` and `T`
genuinely differ in what they permit, unlike for an immutable one.
"""

from immutablepy import Mut


def get_value() -> list[int]:
    return [5]


y: list[int] = get_value()
x: Mut[list[int]] = y
