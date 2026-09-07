"""Control case for `mut_check`'s private view.

A for-loop that only reads its target needs no `Mut[T]` pre-declaration and
no filter -- pre-declaring `Mut[int]` (see
mut_check_predeclared_for_loop.py) is only justified when the loop body
reassigns or mutates the target. Each iteration's binding is effectively
fresh, like the construction exemption, not a reassignment needing
permission.
"""

for i in range(5):
    print(i)
