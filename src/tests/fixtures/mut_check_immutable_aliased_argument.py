"""Immutable-type exemption target, argument-passing shape.

Same exemption as mut_check_immutable_aliased_assignment_int.py, but `ty`
renders argument-passing mismatches under a different diagnostic code and
message shape (`invalid-argument-type`, "Expected `Mut[int]`, found `int`")
than plain assignment (`invalid-assignment`, "is not assignable to
`Mut[int]`"). The immutable exemption must apply to both shapes uniformly.
"""

from immutablepy import Mut


def f(_x: Mut[int]) -> None: ...


def g(y: int) -> None:
    f(y)
