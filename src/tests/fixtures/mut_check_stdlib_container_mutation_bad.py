"""Only meaningful under `mut_check`'s private, intersection-based view.

Mirrors `mut_check_stdlib_container_mutation_ok.py` exactly, method for
method, but with a plain (non-`Mut`) receiver throughout -- every single call
here must be rejected.
"""


def list_mutation_bad(xs: list[int]) -> None:
    xs.append(1)
    xs.extend([2, 3])
    xs.insert(0, 0)
    xs.remove(1)
    xs.sort()
    xs.pop()
    xs.__setitem__(0, 1)
    xs.__delitem__(0)
    xs.clear()
    xs.reverse()


def dict_mutation_bad(d: dict[str, int]) -> None:
    d.__setitem__("a", 1)
    d.__delitem__("a")
    d.pop("a", 0)
    d.__ior__({"b": 2})
    d.clear()
    d.popitem()
    d.setdefault("c", 3)
    d.update({"d": 4})


def set_mutation_bad(s: set[int]) -> None:
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
    s.clear()
    s.pop()


def bytearray_mutation_bad(b: bytearray) -> None:
    b.append(1)
    b.extend([2, 3])
    b.insert(0, 0)
    b.remove(1)
    b.pop()
    b.__setitem__(0, 1)
    b.__delitem__(0)
    b.__iadd__(b"x")
    b.__imul__(2)
    b.clear()
    b.reverse()
