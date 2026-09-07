"""Only meaningful under `mut_check`'s private, intersection-based view.

Pre-declared for-loop target, per CLAUDE.md's "no post-assignment
annotation" pattern -- but pre-declaring `Mut[int]` is only actually
justified here because the loop body reassigns `i` (`i += 1`); a loop that
only reads its target needs no `Mut` at all. Confirmed via the checker's raw
diagnostics that both the implicit per-iteration binding and the augmented
assignment produce the same `invalid-assignment` diagnostic code as plain
assignment, but WITHOUT the `MutMarker` explanation in their message --
unlike plain assignment/unpacking. The message-substring filter as
originally specced would miss this case.
"""

from typing import reveal_type

from immutablepy import Mut

i: Mut[int]
for i in range(5):
    i += 1
    reveal_type(i)
