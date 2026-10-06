"""Three shapes `mut_check._reassignment` must handle, each a real violation:

* `*args`/`**kwargs` are bound from the call and never `Mut`, so reassigning
  either is a violation just like any plain parameter.
* A `Mut` annotation that lives only inside an `except` handler still opts
  the whole function in, so the violation in the `try` body is caught.
* A lambda's own parameters are scoped to the lambda and restored on exit --
  `x` below keeps its binding from before the lambda, so its second
  assignment is still a violation.
"""

from immutablepy import Mut


def varargs(*args: int, **kwargs: int) -> None:
    _opt_in: Mut[int] = 0
    args = ()
    kwargs = {}


def try_body(_x: int) -> None:
    try:
        _x = 1
    except ValueError:
        _opt_in: Mut[int] = 0


def lambda_scope_restored() -> None:
    _opt_in: Mut[int] = 0
    x = 1
    print(sorted([2, 1], key=lambda x: x))
    x = 2
