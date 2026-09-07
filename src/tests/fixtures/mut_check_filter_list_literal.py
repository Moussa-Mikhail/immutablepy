"""Construction/literal exemption target for `mut_check`'s diagnostic filter.

Same as the `int` case, for a `list` literal (a container, not just a scalar).
"""

from immutablepy import Mut

items: Mut[list[int]] = [1, 2, 3]
