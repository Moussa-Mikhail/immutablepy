"""Control case: the same mutation as mut_check_reassignment_loop_var_without_mut.py,
but `i` is pre-declared `Mut[int]` -- permitted.
"""

from immutablepy import Mut

i: Mut[int]
for i in range(5):
    i += 1
