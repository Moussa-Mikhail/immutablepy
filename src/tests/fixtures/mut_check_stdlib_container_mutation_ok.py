"""Only meaningful under `mut_check`'s private, intersection-based view.

Pins the vendored typeshed fork's `Mut`-aware stdlib container stubs
(`stubs/typeshed/stdlib/builtins.pyi`/`typing.pyi`): every mutating method on
`list`/`dict`/`set`/`bytearray` must accept a `Mut[...]`-typed receiver --
both the type's own overridden methods and the methods it inherits
un-overridden from its `Mutable*` mixin (`MutableSequence`/`MutableMapping`/
`MutableSet` in `typing.pyi`), since those needed the same `self: Mut[Self]`
-> `self: Mut[S]` fix independently and have regressed before (see
`docs/decisions.md`'s stdlib section). Deliberately avoids subscript syntax
(`d[k] = v`) -- that's a separate, still-open `ty` bug (see
`docs/decisions.md`'s "Open `ty` bug: subscript syntax..." section) that
fails regardless of `Mut`, so it would fail this file for the wrong reason.
Explicit dunder calls stand in for it instead.
"""

from immutablepy import Mut


def list_mutation_ok(xs: Mut[list[int]]) -> None:
    xs.append(1)
    xs.extend([2, 3])
    xs.insert(0, 0)
    xs.remove(1)
    xs.sort()
    xs.pop()
    xs.__setitem__(0, 1)
    xs.__delitem__(0)
    xs += [4]  # __iadd__, list's own override
    xs.clear()  # inherited from MutableSequence, not overridden by list
    xs.reverse()  # inherited from MutableSequence, not overridden by list


def dict_mutation_ok(d: Mut[dict[str, int]]) -> None:
    d.__setitem__("a", 1)
    d.__delitem__("a")
    d.pop("a", 0)
    d.__ior__({"b": 2})
    d.clear()  # inherited from MutableMapping, not overridden by dict
    d.popitem()  # inherited from MutableMapping, not overridden by dict
    d.setdefault("c", 3)  # inherited from MutableMapping, not overridden by dict
    d.update({"d": 4})  # inherited from MutableMapping, not overridden by dict


def set_mutation_ok(s: Mut[set[int]]) -> None:
    s.add(1)
    s.discard(1)
    s.remove(1)
    s.update({2, 3})
    s.difference_update({4})
    s.intersection_update({1, 2, 3})
    s.symmetric_difference_update({5})
    s.__ior__({6})
    s.__iand__({1, 2})
    s.__isub__({7})
    s.__ixor__({8})
    s.clear()  # inherited from MutableSet, not overridden by set
    s.pop()  # inherited from MutableSet, not overridden by set


def bytearray_mutation_ok(b: Mut[bytearray]) -> None:
    b.append(1)
    b.extend([2, 3])
    b.insert(0, 0)
    b.remove(1)
    b.pop()
    b.__setitem__(0, 1)
    b.__delitem__(0)
    b.__iadd__(b"x")
    b.__imul__(2)
    b.clear()  # inherited from MutableSequence, not overridden by bytearray
    b.reverse()  # inherited from MutableSequence, not overridden by bytearray
