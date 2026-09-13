"""No `Mut` anywhere -- `ty` has no notion of "unannotated local is
read-only" at all, so it reports zero diagnostics for this. Only
`mut_check`'s own custom check (`mut_check._reassignment`) catches it.
"""

for i in range(5):
    i += 1
