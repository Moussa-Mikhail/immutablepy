"""
mut_check: the tool's own private, intersection-based static check.

Wraps the bundled `ty` binary, configured (via `_ty_project/ty.toml`) to
resolve `immutablepy` to the intersection-based internal stub
(`stubs/internal/`) instead of the plain public alias real type checkers
see. `ty` is an implementation detail of this wrapper -- callers shouldn't
need to know it's `ty` underneath, and this is the only place that should.

Currently, a thin subprocess wrapper; per CLAUDE.md this will eventually
drive the bundled `ty` via LSP (`didOpen`/`didChange`, reading
`publishDiagnostics`) instead of one-shot `ty check` invocations.
"""

import subprocess
import sys
from pathlib import Path

_TY_PROJECT_DIR = Path(__file__).resolve().parent / "_ty_project"


def check(*paths: str | Path) -> subprocess.CompletedProcess[str]:
    """Run the private static check against `paths`, returning the raw result."""
    return subprocess.run(  # noqa: S603 # fixed argv, no shell, `paths` are just file arguments
        [sys.executable, "-m", "ty", "check", "--project", str(_TY_PROJECT_DIR), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
        check=False,
    )
