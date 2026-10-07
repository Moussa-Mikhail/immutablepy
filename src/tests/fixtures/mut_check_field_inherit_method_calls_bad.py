"""Only meaningful under `mut_check`'s private, intersection-based view.

Guards the `MutMarker.__getattr__` union in stubs/internal: if attribute access
through a `Mut` owner ever collapsed methods to `Never` (a bare `-> MutMarker`
does, because a bound method and a `MutMarker` instance are disjoint), these
wrong-argument calls would silently stop being reported. Instance, static and
class methods each need their own union member to survive.
"""

from typing import Self

from immutablepy import Mut


class Util:
    def instance(self: Mut[Self], x: int) -> None: ...

    @staticmethod
    def static(x: int) -> None: ...

    @classmethod
    def klass(cls, x: int) -> None: ...


def wrong_args(u: Mut[Util]) -> None:
    u.instance("a")
    u.static("b")
    u.klass("c")
