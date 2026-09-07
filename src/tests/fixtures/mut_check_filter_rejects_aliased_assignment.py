"""Control case: the filter must not overreach.

Same `AnnAssign` shape as the literal fixtures (`x: Mut[T] = <value>`), but
the value is a plain variable reference, not a literal display -- the
filter's AST check must tell these apart and leave this one rejected.
"""

from immutablepy import Mut


def get_value() -> int:
    return 5


y: int = get_value()
x: Mut[int] = y
