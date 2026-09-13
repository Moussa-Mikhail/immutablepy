"""
Invoke the bundled `ty` binary and parse its output into `Diagnostic`s.

Uses `ty`'s default (human-oriented) rendering, not a machine-readable
`--output-format`, so that a diagnostic's `Diagnostic.text` is exactly what
`ty check` itself would print -- `immut check`'s output should look like
`ty check`'s. Diagnostics are separated by blank lines; each starts with a
`severity[code]: message` header and has its primary location on the next
`--> file:line:col` line.

This is the only module that knows the result comes from `ty` at all.
"""

import re
import subprocess
import sys
from pathlib import Path

from immutablepy import Mut
from mut_check._diagnostics import Diagnostic

_TY_PROJECT_DIR = Path(__file__).resolve().parent / "_ty_project"

_HEADER = re.compile(r"^(error|warning|info)\[([a-z0-9-]+)\]:")
_LOCATION = re.compile(r"^\s*--> (?P<file>.+):(?P<line>\d+):(?P<col>\d+)$")


def _parse(stdout: str) -> Mut[list[Diagnostic]]:
    diagnostics: Mut[list[Diagnostic]] = []
    for block in stdout.split("\n\n"):
        lines = block.splitlines()
        if not lines:
            continue
        header = _HEADER.match(lines[0])
        if not header:
            continue
        for line_text in lines[1:]:
            location = _LOCATION.match(line_text)
            if location:
                diagnostics.append(
                    Diagnostic(
                        severity=header.group(1),
                        code=header.group(2),
                        file=Path(location["file"]),
                        line=int(location["line"]),
                        col=int(location["col"]),
                        text=block,
                    ),
                )
                break
    return diagnostics


def run(*paths: str | Path) -> Mut[list[Diagnostic]]:
    """Run the private, intersection-based check against `paths`."""
    result = subprocess.run(  # noqa: S603 # fixed argv, no shell, `paths` are just file arguments
        [sys.executable, "-m", "ty", "check", "--project", str(_TY_PROJECT_DIR), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
        check=False,
    )
    return _parse(result.stdout)
