"""Only meaningful under `mut_check`'s private, intersection-based view.

`y` is a plain `int` parameter -- not locally constructed, potentially
aliased elsewhere -- so it genuinely lacks `MutMarker`. The private check
must reject passing it where `Mut[int]` is expected; this is a true
positive that the tool's (not yet built) diagnostic filter must never
suppress, unlike the literal/construction false positives it's meant for.
"""

from immutablepy import Mut


def f(_x: Mut[int]) -> None: ...


def g(y: int) -> None:
    f(y)
