"""Only meaningful under `mut_check`'s private, intersection-based view.

Pre-declared for-loop target, per CLAUDE.md's "no post-assignment
annotation" pattern. Confirmed via the checker's raw diagnostics that this
produces the same `invalid-assignment` diagnostic code as plain assignment,
but WITHOUT the `MutMarker` explanation in its message -- unlike plain
assignment/unpacking. The message-substring filter as originally specced
would miss this case.
"""

from typing import reveal_type

from immutablepy import Mut

i: Mut[int]
for i in range(5):
    reveal_type(i)
