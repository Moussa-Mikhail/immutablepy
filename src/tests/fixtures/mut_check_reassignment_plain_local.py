"""A plain local's first assignment is always free; the second one, without
`Mut`, is a violation `mut_check._reassignment` catches (`ty` doesn't) --
once this module's opted in via a `Mut` annotation of its own, per
CLAUDE.md's "Incremental adoption" ratchet.
"""

from immutablepy import Mut

x = 5
# noinspection redeclaration
x = 6

_opt_in: Mut[int] = 0
