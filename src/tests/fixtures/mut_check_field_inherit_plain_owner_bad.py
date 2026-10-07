"""Only meaningful under `mut_check`'s private, intersection-based view.

Control for mut_check_field_inherit_mut_owner_ok.py: the same mutations through
a *plain* (read-only) owner must be rejected -- inside a method whose `self`
isn't `Mut`, on a plain parameter, and through a chain of attributes. The
field's contents inherit the owner's read-only-ness.
"""


class Bag:
    def __init__(self) -> None:
        self.items: list[int] = []

    def peek(self) -> None:
        self.items.append(1)


class Holder:
    def __init__(self) -> None:
        self.bag = Bag()


def read_only(b: Bag) -> None:
    b.items.append(2)


def read_only_nested(h: Holder) -> None:
    h.bag.items.append(3)
