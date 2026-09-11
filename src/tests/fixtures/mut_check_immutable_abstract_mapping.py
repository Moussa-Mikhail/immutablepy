"""Same exemption as mut_check_immutable_abstract_sequence.py, for `Mapping`.

`Mapping[K, V]` has no mutating members in its own definition (no
`__setitem__`, no `pop`) -- covers a second read-only abstract type so the
exemption isn't verified against `Sequence` alone.
"""

from collections.abc import Mapping

from immutablepy import Mut


def get_value() -> Mapping[str, int]:
    return {"a": 1}


y: Mapping[str, int] = get_value()
x: Mut[Mapping[str, int]] = y
