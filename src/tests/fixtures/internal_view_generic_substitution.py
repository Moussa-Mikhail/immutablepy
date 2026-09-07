"""Only meaningful under the tool's private, intersection-based `ty` view.

Intersections must survive generic substitution: a field declared `Mut[T]`
on a generic class, specialized with a plain type argument, must still
reveal the `MutMarker`-carrying type -- not degrade to the plain type.
"""

from typing import reveal_type

from immutablepy import Mut


class Container[T]:
    item: Mut[T]


def get_item(c: Container[int]) -> None:
    reveal_type(c.item)
