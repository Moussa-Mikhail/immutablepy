"""Only meaningful under `mut_check`'s private, intersection-based view.

Pre-declared `with`-statement target, per CLAUDE.md's "no post-assignment
annotation" pattern. `StringIO` is mutable (not on the immutable allowlist),
but `filter_construction_exemption` treats the target-binding diagnostic as
exempt regardless of type -- see its module docstring for why that's sound.
`check()` must come back clean.
"""

import io
from typing import reveal_type

from immutablepy import Mut

f: Mut[io.StringIO]
with io.StringIO() as f:
    reveal_type(f)
