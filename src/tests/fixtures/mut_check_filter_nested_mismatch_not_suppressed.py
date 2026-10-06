"""Only meaningful under `mut_check`'s private, intersection-based view.

A protocol method promising `Mut[list[int]]` against an implementation that
returns plain `list[int]` is a real mismatch -- `ty` reports it as a tree
whose only `Mut[` mention (`list[int]` is not assignable to `Mut[list[int]]`)
sits on a nested `└──` line, at the position of `HandsOutReadOnly()`, a call
to a locally-defined class. That position alone looks like a fresh
construction, so `mut_check._filter` would suppress it as its construction
false positive if it didn't ignore nested lines -- the error would vanish.
"""

from typing import Protocol

from immutablepy import Mut


class HandsOutMutable(Protocol):
    def get(self) -> Mut[list[int]]: ...


class HandsOutReadOnly:
    def get(self) -> list[int]:
        return []


def use(_x: HandsOutMutable) -> None: ...


use(HandsOutReadOnly())
