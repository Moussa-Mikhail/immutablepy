"""Construction/literal exemption target for `mut_check`'s diagnostic filter.

Same as the `int` case, for a `set` literal.
"""

from immutablepy import Mut

items: Mut[set[int]] = {1, 2, 3}
