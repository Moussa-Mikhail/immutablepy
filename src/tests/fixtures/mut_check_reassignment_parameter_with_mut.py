"""Control case: the same reassignment as mut_check_reassignment_parameter.py,
but `x` is declared `Mut[int]` -- permitted.
"""

from immutablepy import Mut


def f(_x: Mut[int]) -> None:
    _x = 5
