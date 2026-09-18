"""Only meaningful under `mut_check`'s private, intersection-based view.

Unlike mut_check_unpacking_without_mut.py, `a` is genuinely mutable
(`list[int]`, not on the immutable allowlist). `get_values` is an ordinary
function, not a class or a built-in mutable-container constructor, so
calling it carries no language-level freshness guarantee; its *declared*
return type (`tuple[list[int], list[int]]`, plain, no `Mut` anywhere) is a
real prior type commitment the caller can't override, regardless of what
the body happens to do internally. Pre-declaring `Mut[list[int]]` is
genuinely needed, and unpacking a value of that already-committed plain
type into it is still correctly rejected -- the same type mismatch as
mut_check_rejects_aliased_t.py, just via unpacking syntax.
"""

from immutablepy import Mut


def get_values() -> tuple[list[int], list[int]]:
    return [1], [2]


a: Mut[list[int]]
b: list[int]
a, b = get_values()
