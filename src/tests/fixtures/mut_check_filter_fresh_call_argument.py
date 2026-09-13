"""Only meaningful under `mut_check`'s private, intersection-based view.

A freshly-constructed value (a bare-name call, `Box()`) passed directly as
a call argument must satisfy a `Mut[...]`-typed parameter -- same
construction exemption as an `AnnAssign`, at the call-argument position.
"""

from immutablepy import Mut


class Box:
    value: int


def f(_b: Mut[Box]) -> None: ...


f(Box())
