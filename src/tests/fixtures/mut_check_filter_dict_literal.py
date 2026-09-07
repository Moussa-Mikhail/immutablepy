"""Construction/literal exemption target for `mut_check`'s diagnostic filter.

Same as the `int` case, for a `dict` literal.
"""

from immutablepy import Mut

mapping: Mut[dict[str, int]] = {"a": 1}
