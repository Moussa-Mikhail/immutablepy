"""Control case for mut_check_filter_nested_mismatch_not_suppressed.py: the
implementation's `get` returns `Mut[list[int]]`, matching the protocol, so
there is no mismatch and nothing for the filter to decide -- clean.
"""

from typing import Protocol

from immutablepy import Mut


class HandsOutMutable(Protocol):
    def get(self) -> Mut[list[int]]: ...


class HandsOutMutableToo:
    def get(self) -> Mut[list[int]]:
        return []


def use(_x: HandsOutMutable) -> None: ...


use(HandsOutMutableToo())
