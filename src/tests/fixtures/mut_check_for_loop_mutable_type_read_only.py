"""Control case for `mut_check`'s private view.

Same as mut_check_for_loop_read_only_needs_no_mut.py, but with a genuinely
mutable type (`Box`) instead of `int` -- a for-loop that only reads its
target needs no `Mut[T]` pre-declaration regardless of the target's type.
`reveal_type` confirms the binding stays plain `Box`, not `Box & MutMarker`.
"""

from typing import reveal_type


class Box:
    value: int


for b in (Box(), Box()):
    reveal_type(b)
