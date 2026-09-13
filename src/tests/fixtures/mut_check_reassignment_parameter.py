"""A parameter is bound from the moment of the call -- unlike a fresh local,
there's no free first assignment inside the body, so even this single
reassignment is a violation without `Mut`.
"""


def f(_x: int) -> None:
    _x = 5
