"""Only meaningful under `mut_check`'s private, intersection-based view.

`list()` (a built-in mutable-container constructor) has the same
language-level freshness guarantee as a locally-defined class -- must
satisfy `Mut[list[int]]` the same as a literal `[]` would.
"""

from immutablepy import Mut

x: Mut[list[int]] = list()
