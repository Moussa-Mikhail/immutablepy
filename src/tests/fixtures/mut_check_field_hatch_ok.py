"""Only meaningful under `mut_check`'s private, intersection-based view.

Escape hatch: a field annotated with an outer `Mut` stays mutable through *any*
owner, even a plain one -- interior state such as a memo or a counter that a
logically read-only method updates. Initialization uses both attribute-target
forms (`self.memo = {}` and `self.hits: Mut[...] = []`); each is a fresh value,
so it satisfies the `Mut` field.
"""

from immutablepy import Mut


class Cache:
    memo: Mut[dict[str, int]]

    def __init__(self) -> None:
        self.memo = {}
        self.hits: Mut[list[int]] = []

    def lookup(self, key: str) -> int:
        self.memo.update({key: 1})
        self.hits.append(1)
        return self.memo.get(key, 0)


def warm(c: Cache) -> None:
    c.memo.update({"a": 1})
