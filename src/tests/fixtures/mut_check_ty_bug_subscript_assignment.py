"""Only meaningful under `mut_check`'s private, intersection-based view.

`xs[0] = 1` on a genuinely `Mut[list[int]]` receiver -- `ty` should accept
this (the equivalent `xs.__setitem__(0, 1)` call does, on the identical
receiver -- see mut_check_stdlib_container_mutation_ok.py) but currently
doesn't. See test_ty_bugs.py.
"""

from immutablepy import Mut


def subscript_assignment_on_mut_receiver(xs: Mut[list[int]]) -> None:
    xs[0] = 1
