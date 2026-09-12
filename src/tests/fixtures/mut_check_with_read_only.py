"""Control case for `mut_check`'s private view.

A `with`-statement target that's only read needs no `Mut[T]` pre-declaration
at all -- same "no post-assignment annotation" constraint as for-loops only
matters when the target is later reassigned/mutated. `reveal_type` confirms
the binding stays plain `StringIO`, not `StringIO & MutMarker`.
"""

import io
from typing import reveal_type

with io.StringIO() as f:
    reveal_type(f)
