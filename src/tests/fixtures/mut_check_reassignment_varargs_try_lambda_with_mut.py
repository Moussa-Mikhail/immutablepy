"""Control cases for mut_check_reassignment_varargs_try_lambda.py -- each of
these is permitted:

* `*args` can't carry `Mut` on the parameter itself (that annotation
  describes each element, not the binding), so the only opt-in is
  redeclaring the name in the body -- see docs/decisions.md's "Known
  limitation: `*args`/`**kwargs`" note. This pins that the redeclared form
  is accepted.
* The `try`-body reassignment is permitted once the parameter is `Mut`.
* The post-lambda reassignment is permitted once `x` is declared `Mut`.
"""

from immutablepy import Mut


def varargs_redeclared(*args: int) -> None:
    args: Mut[tuple[int, ...]] = args  # noqa: PLW0127 -- the self-assignment *is* the redeclaration
    args = ()


def try_body(_x: Mut[int]) -> None:
    try:
        _x = 1
    except ValueError:
        print(_x)


def lambda_scope_restored() -> None:
    x: Mut[int] = 1
    print(sorted([2, 1], key=lambda x: x))
    x = 2
