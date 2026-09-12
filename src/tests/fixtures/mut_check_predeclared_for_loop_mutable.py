"""Only meaningful under `mut_check`'s private, intersection-based view.

Same pre-declared for-loop target as mut_check_predeclared_for_loop.py, but
with a genuinely mutable type (`Box`, not on the immutable allowlist)
instead of `int` -- confirms `filter_construction_exemption`'s for/with
target handling doesn't depend on the target's type. `check()` must come
back clean, same as the immutable case.
"""

from immutablepy import Mut


class Box:
    value: int


b: Mut[Box]
for b in (Box(), Box()):
    pass
