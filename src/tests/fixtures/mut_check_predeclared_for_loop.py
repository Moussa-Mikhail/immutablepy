"""Only meaningful under `mut_check`'s private, intersection-based view.

Pre-declared for-loop target, per CLAUDE.md's "no post-assignment
annotation" pattern -- pre-declaring `Mut[int]` is actually justified here
(unlike mut_check_for_loop_mutable_type_read_only.py) because the loop body
reassigns `i` (`i += 1`); a loop that only reads its target needs no `Mut`
at all. The checker's raw diagnostics for both the implicit per-iteration
binding and the augmented assignment produce the same `invalid-assignment`
code as plain assignment, but WITHOUT the `MutMarker` explanation in their
message -- unlike plain assignment/unpacking. `int` is immutable though, so
`filter_immutable_type_exemption` (which falls back to the primary message
when the info line is missing) covers the augmented assignment regardless,
and `filter_construction_exemption` covers the for-loop target-binding
unconditionally: `check()` must still come back clean.
"""

from typing import reveal_type

from immutablepy import Mut

i: Mut[int]
for i in range(5):
    i += 1
    reveal_type(i)
