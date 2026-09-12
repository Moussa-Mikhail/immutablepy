"""Only meaningful under `mut_check`'s private, intersection-based view.

Same pre-declared for-loop target gap as mut_check_predeclared_for_loop.py,
but with a genuinely mutable type (`Box`, not on the immutable allowlist)
instead of `int` -- confirms the gap is still real for mutable types.
Neither filter reaches this: `filter_construction_exemption` only inspects
`AnnAssign` nodes (a `for` target is a different AST shape entirely), and
`filter_immutable_type_exemption` only exempts types on its allowlist.
"""

from immutablepy import Mut


class Box:
    value: int


b: Mut[Box]
for b in [Box(), Box()]:
    pass
