"""Control case for `mut_check`'s private view.

Per CLAUDE.md: "Unpacking without pre-declaration produces immutable
bindings by default." No `Mut` pre-declaration needed at all when the
unpacked targets are only read afterward. `reveal_type` confirms the
bindings stay plain `Literal[1]`/`Literal[2]`, not `& MutMarker`.
"""

from typing import reveal_type

a, b = (1, 2)
reveal_type(a)
reveal_type(b)
