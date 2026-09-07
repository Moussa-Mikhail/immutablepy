"""
Invoke the bundled `ty` binary and parse its output into `Diagnostic`s.

`ty` is invoked with `--output-format github`: one line per diagnostic with
explicit `file=`/`line=`/`col=` fields, instead of its default human-oriented
rendering (diagnostics separated by blank lines, location on its own `-->`
line). The github format is exactly as information-preserving -- the full
multi-line message, including nested `info:` explanations, is still present
after the `::`, just newline-escaped as `%0A` -- while being unambiguous to
parse: no guessing where one diagnostic's text ends and the next begins.

This is the only module that knows the result comes from `ty` at all, or
that its wire format is GitHub Actions annotation syntax.
"""

import re
import subprocess
import sys
from pathlib import Path

from mut_check._diagnostics import Diagnostic

_TY_PROJECT_DIR = Path(__file__).resolve().parent / "_ty_project"

_ANNOTATION = re.compile(
    r"^::(error|warning|notice) title=ty \(([a-z0-9-]+)\),file=(?P<file>.+),"
    r"line=(?P<line>\d+),col=(?P<col>\d+),endLine=\d+,endColumn=\d+::(?P<message>.*)$",
)

# ty's own message already repeats "path:line:col: code: " at the start (using
# whatever path it was invoked with, which may not match the `file=` field's
# absolute path) -- Diagnostic.message should carry only the human-readable text.
_REDUNDANT_PREFIX = re.compile(r"^\S+:\d+:\d+: [a-z0-9-]+: ")


def _parse(stdout: str) -> list[Diagnostic]:
    diagnostics = []
    for raw_line in stdout.splitlines():
        match = _ANNOTATION.match(raw_line)
        if not match:
            continue
        message = match["message"].replace("%0A", "\n")
        message = _REDUNDANT_PREFIX.sub("", message, count=1)
        diagnostics.append(
            Diagnostic(
                severity=match.group(1),
                code=match.group(2),
                file=Path(match["file"]),
                line=int(match["line"]),
                col=int(match["col"]),
                message=message,
            ),
        )
    return diagnostics


def run(*paths: str | Path) -> list[Diagnostic]:
    """Run the private, intersection-based check against `paths`."""
    result = subprocess.run(  # noqa: S603 # fixed argv, no shell, `paths` are just file arguments
        [
            sys.executable,
            "-m",
            "ty",
            "check",
            "--output-format",
            "github",
            "--project",
            str(_TY_PROJECT_DIR),
            *(str(p) for p in paths),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return _parse(result.stdout)
