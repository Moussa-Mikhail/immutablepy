"""Only meaningful under `mut_check`'s private, intersection-based view.

`y` is a plain `list[int]` parameter -- not locally constructed, potentially
aliased elsewhere -- so it genuinely lacks `MutMarker`. Unlike immutable
types (see CLAUDE.md's "Immutable types always satisfy Mut[T]"), aliasing
a mutable value like a list is a real hazard: the private check must reject
passing it where `Mut[list[int]]` is expected; this is a true positive that
the tool's (not yet built) diagnostic filter must never suppress, unlike the
literal/construction false positives it's meant for.
"""

from immutablepy import Mut


def f(_x: Mut[list[int]]) -> None: ...


def g(y: list[int]) -> None:
    f(y)
