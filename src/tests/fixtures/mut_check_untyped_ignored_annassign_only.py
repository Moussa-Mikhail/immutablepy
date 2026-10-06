"""The only annotation anywhere in this file is one `AnnAssign` (`_opt_in`),
no parameter or return annotation -- that alone must be enough for
`"ignored"` mode to keep parsing the file instead of skipping it, so `x`'s
reassignment is still reported (`f` is opted in by that same `Mut`).
"""

from immutablepy import Mut


def f():
    _opt_in: Mut[int] = 0
    x = 1
    x = 2
    print(x)
