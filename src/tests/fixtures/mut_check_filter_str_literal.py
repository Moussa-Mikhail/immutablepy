"""Construction/literal exemption target for `mut_check`'s diagnostic filter.

Same as the `int` case, for `str`.
"""

from immutablepy import Mut

s: Mut[str] = "hello"
