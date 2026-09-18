"""Only meaningful under `mut_check`'s private, intersection-based view.

`y` is a plain `list[int]` parameter -- not locally constructed -- so its
type is already committed as plain `list[int]` by its own declaration, and
it genuinely lacks `MutMarker`. Unlike immutable types (see CLAUDE.md's
"Immutable types always satisfy Mut[T]"), `Mut[list[int]]` and `list[int]`
genuinely differ in what they permit, so the private check must reject
passing it where `Mut[list[int]]` is expected; this is a true positive that
the tool's (not yet built) diagnostic filter must never suppress, unlike the
literal/construction false positives it's meant for.
"""

from immutablepy import Mut


def f(_x: Mut[list[int]]) -> None: ...


def g(y: list[int]) -> None:
    f(y)
