"""Construction/literal exemption target for `mut_check`'s diagnostic filter.

A plain `int` literal assigned directly to a `Mut[int]`-declared binding is a
fresh, unaliased value -- per CLAUDE.md's construction exemption, this must
type-check clean through `mut_check`, even though the underlying checker
raises a `MutMarker` false positive for it today.
"""

from immutablepy import Mut

x: Mut[int] = 5
