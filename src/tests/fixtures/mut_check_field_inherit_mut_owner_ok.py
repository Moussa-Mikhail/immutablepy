"""Only meaningful under `mut_check`'s private, intersection-based view.

Fields inherit mutability from their owner: through a `Mut` owner -- including
`self` in a `Mut[Self]` method, and through a chain of attributes -- mutating a
field's contents is permitted, with the field itself declared plain. Calls to
instance, static and class methods through a `Mut` owner type-check normally.
"""

from typing import Self

from immutablepy import Mut


class Bag:
    def __init__(self) -> None:
        self.items: list[int] = []

    def add(self: Mut[Self], x: int) -> None:
        self.items.append(x)


class Holder:
    def __init__(self) -> None:
        self.bag = Bag()


class Util:
    def instance(self: Mut[Self], x: int) -> None: ...

    @staticmethod
    def static(x: int) -> None: ...

    @classmethod
    def klass(cls, x: int) -> None: ...


def fill(b: Mut[Bag]) -> None:
    b.items.append(1)


def fill_nested(h: Mut[Holder]) -> None:
    h.bag.items.append(1)


def calls(u: Mut[Util]) -> None:
    u.instance(1)
    u.static(1)
    u.klass(1)
