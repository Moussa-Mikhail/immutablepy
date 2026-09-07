"""Only meaningful under the tool's private, intersection-based `ty` view.

Fresh literal assigned directly to a `Mut[T]`-declared binding. Per
CLAUDE.md's construction exemption, this must eventually be treated as
allowed -- but `ty` itself has no notion of "freshness" and raises the same
`MutMarker` false positive as an aliased value would. See
test_internal_ty_intersection.py for the exact message shape this produces.
"""

from typing import reveal_type

from immutablepy import Mut

x: Mut[list[int]] = [1, 2, 3]
reveal_type(x)
