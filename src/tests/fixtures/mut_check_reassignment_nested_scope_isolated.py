"""A nested function's local shadows the outer one -- reassigning `x` in
`inner` doesn't touch `outer`'s `x` at all, but `inner`'s own second
assignment to its own `x` is still a real, separate violation.
"""


def outer() -> None:
    _x = 1

    # noinspection shadowing-names
    def inner() -> None:
        _x = 2
        _x = 3

    inner()
    print(_x)
