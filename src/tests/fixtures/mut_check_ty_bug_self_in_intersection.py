"""Only meaningful under `mut_check`'s private, intersection-based view.

`self: Mut[Self]` on a parameterized generic class, called on a genuinely
`Mut[Box[int]]` receiver -- `ty` should accept this but doesn't: `Self`
inside an `Intersection` fails to substitute the enclosing class's type
parameter before checking it against `Self`'s upper bound. The stdlib
container stubs work around this project-wide with `self: Mut[S]` (`S` a
bound `TypeVar`) instead of `Self` -- see `list.S` in
stubs/typeshed/stdlib/builtins.pyi and test_ty_bugs.py.
"""

from typing import Self

from immutablepy import Mut


class Box[T]:
    def mutate(self: Mut[Self], value: T) -> None:
        pass


def call_on_mut_receiver(b: Mut[Box[int]]) -> None:
    b.mutate(1)
