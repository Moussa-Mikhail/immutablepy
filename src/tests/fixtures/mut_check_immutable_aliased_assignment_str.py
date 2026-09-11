"""Same exemption as mut_check_immutable_aliased_assignment_int.py, for `str`.

Covers a second immutable scalar type so the exemption isn't verified against
`int` alone -- see CLAUDE.md's "Immutable types always satisfy `Mut[T]`".
"""

from immutablepy import Mut


def get_value() -> str:
    return "hi"


y: str = get_value()
x: Mut[str] = y
