"""Only meaningful under `mut_check`'s private, intersection-based view.

Same pre-declared unpacking target as mut_check_predeclared_unpacking.py,
but with a genuinely mutable type (`list[int]`, not on the immutable
allowlist) instead of `int` -- confirms aliasing an unpacked mutable value
is still correctly rejected.
"""

from immutablepy import Mut


def get_values() -> tuple[list[int], list[int]]:
    return [1], [2]


a: Mut[list[int]]
b: list[int]
a, b = get_values()
