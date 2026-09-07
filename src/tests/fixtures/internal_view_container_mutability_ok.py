"""Only meaningful under the tool's private, intersection-based `ty` view.

Both must be accepted with zero errors -- the compositional container
mutability distinction from CLAUDE.md, positive cases:

- `Mut[list[User]]` grants restructuring permission only: appending a plain
  `User` is fine, since the element type itself is just `User`.
- `Mut[list[Mut[User]]]` additionally grants element-mutation permission:
  appending a `Mut[User]` is fine too, since the element type is `Mut[User]`.
"""

from immutablepy import Mut


class User:
    name: str


def append_plain_to_container_only_mut(items: Mut[list[User]], u: User) -> None:
    items.append(u)


def append_mut_to_deeply_mut(items: Mut[list[Mut[User]]], u: Mut[User]) -> None:
    items.append(u)
