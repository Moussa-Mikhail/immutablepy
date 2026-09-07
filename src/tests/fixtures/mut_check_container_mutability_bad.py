"""Only meaningful under `mut_check`'s private, intersection-based view.

Must be rejected: `Mut[list[Mut[User]]]` requires elements to carry
`MutMarker` too -- appending a plain `User` (missing the element-level
permission) must fail, unlike the container-only `Mut[list[User]]` case.
"""

from immutablepy import Mut


class User:
    name: str


def append_plain_to_deeply_mut(items: Mut[list[Mut[User]]], u: User) -> None:
    items.append(u)
