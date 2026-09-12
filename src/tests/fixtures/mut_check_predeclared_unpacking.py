"""Only meaningful under `mut_check`'s private, intersection-based view.

Pre-declared unpacking target, per CLAUDE.md's "no post-assignment
annotation" pattern. Unlike the for-loop/with cases, this one's message
DOES include the `MutMarker` explanation -- same shape as plain assignment.
`int` is immutable though, so `check()` must still come back clean (see
mut_check_predeclared_unpacking_mutable.py for a genuinely mutable type,
still correctly rejected).
"""

from typing import reveal_type

from immutablepy import Mut

a: Mut[int]
b: int
a, b = (1, 2)
reveal_type(a)
reveal_type(b)
