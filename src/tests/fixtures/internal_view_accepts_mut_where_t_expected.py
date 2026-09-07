"""Only meaningful under the tool's private, intersection-based `ty` view.

The forward direction of `Mut[T] <: T`: a `Mut[T]` value must be accepted
anywhere plain `T` is expected, natively, with no filter needed -- `T &
MutMarker` is structurally a subtype of `T`.
"""

from immutablepy import Mut


def f(x: int) -> None: ...


def g(y: Mut[int]) -> None:
    f(y)
