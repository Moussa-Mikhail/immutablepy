"""No `Mut` on `i` itself -- `ty` has no notion of "unannotated local is
read-only" at all, so it reports zero diagnostics for this. Only
`mut_check`'s own custom check (`mut_check._reassignment`) catches it, once
this module's opted in via a `Mut` annotation of its own (`_opt_in` below),
per CLAUDE.md's "Incremental adoption" ratchet.
"""

from immutablepy import Mut

_opt_in: Mut[int] = 0

for i in range(5):
    i += 1
