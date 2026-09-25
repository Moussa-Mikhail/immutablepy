"""Pins a confirmed `ty` bug distinct from mut_self_mypy_bug.py's: `self:
Mut[Self]` is incorrectly rejected when the enclosing class is generic, even
under the public, transparent `Mut[T] = T` alias real users' own `ty`
resolves directly -- not specific to this tool's private, `Intersection`-
based backend. `mut_self_mypy_bug.py`'s `Counter` is non-generic and
unaffected; confirmed the class being generic is what triggers this
(reproduced even with `Mut[T] = T`, no `Intersection` involved at all) -- see
docs/decisions.md's "`ty` bug: `Self` doesn't substitute through a generic type
alias (fixed upstream, unreleased)" section and test_ty_bugs.py. Fixed on `ty`'s
main branch but not yet in a release, so this still passes until a release ships
it; expect it to start failing then, which is the point of the pin.
"""

from typing import Self

from immutablepy import Mut


class Box[T]:
    def mutate(self: Mut[Self], value: T) -> None:
        pass


def call_on_mut_receiver(b: Mut[Box[int]]) -> None:
    b.mutate(1)
