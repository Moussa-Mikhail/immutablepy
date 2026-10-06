"""The only annotations anywhere in this file are on parameters (no
`AnnAssign`, no return annotation) -- that alone must be enough for
`"ignored"` mode to keep parsing the file instead of skipping it. `_m`'s
`Mut` opts `f` in, so `_x`'s reassignment (a plain parameter) is reported.
"""

from immutablepy import Mut


def f(_m: Mut[int], _x: int):
    _x = 5
    return _m
