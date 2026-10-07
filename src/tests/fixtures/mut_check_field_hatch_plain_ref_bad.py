"""Only meaningful under `mut_check`'s private, intersection-based view.

Control for mut_check_field_hatch_ok.py: an always-mutable field still can't be
handed a plain (read-only) reference -- that would give mutation access to
something whose other holders can't mutate it. Rejected both in the
constructor and through another object.
"""

from immutablepy import Mut


class Cache:
    memo: Mut[dict[str, int]]

    def __init__(self, seed: dict[str, int]) -> None:
        self.memo = seed


def adopt(c: Cache, seed: dict[str, int]) -> None:
    c.memo = seed
