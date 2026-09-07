"""
Public API of immutablepy.

Users' own type checkers (mypy, pyright, a plain `ty` install) resolve this
module directly and see `Mut[T]` as a transparent alias for `T` — zero
configuration, zero breakage.
"""

from collections.abc import Callable

type Mut[T] = T


def mut_method[F: Callable[..., object]](method: F) -> F:
    """
    Mark a method as mutating `self` (equivalent to `self: Mut[Self]`).

    A no-op, signature-preserving decorator to real type checkers — it exists
    to be recognized by this tool's own static pass, sidestepping mypy's bug
    on wrapping `Self` in a generic alias for an explicit `self` annotation.
    """
    return method


def mut[T](value: T) -> Mut[T]:
    """
    Assert that `value` may be treated as `Mut[T]`.

    An escape hatch for this tool's static analysis, analogous to
    `typing.cast`: no runtime effect, pure override of what the checker can
    otherwise prove about `value`.
    """
    return value


__all__ = ["Mut", "mut", "mut_method"]
