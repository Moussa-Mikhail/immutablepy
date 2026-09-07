"""Only meaningful under the tool's private, intersection-based `ty` view.

Pre-declared `with`-statement target, per CLAUDE.md's "no post-assignment
annotation" pattern. Same message-shape gap as the for-loop case: no
`MutMarker` explanation in the diagnostic message.
"""

import io
from typing import reveal_type

from immutablepy import Mut

f: Mut[io.StringIO]
with io.StringIO() as f:
    reveal_type(f)
