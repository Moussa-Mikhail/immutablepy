"""
Command-line entry point for the `immut` script.

Uses an explicit `check` subcommand, matching `ruff check`/`ty check`, since
CLAUDE.md already commits to a second, fundamentally different mode later
(driving the bundled `ty` via LSP instead of one-shot invocation) -- the
same relationship as `ty check` vs `ty server`. Making `check` explicit now
avoids a breaking change to add that second mode later.

Renders `mut_check.check`'s structured `Diagnostic`s as plain readable text
for a terminal -- this is the CLI's own presentation, not `ty`'s raw output
shape, so a future `immut server` (LSP) can render the exact same
diagnostics as `publishDiagnostics` JSON instead without this module
needing to change at all.
"""

import sys

from mut_check import Diagnostic, check

_USAGE = "usage: immut check <path> [<path> ...]"


def _render(diagnostic: Diagnostic) -> str:
    location = f"{diagnostic.file}:{diagnostic.line}:{diagnostic.col}"
    return f"{location}: {diagnostic.severity}[{diagnostic.code}]: {diagnostic.message}"


def main() -> int:
    """Dispatch the `immut` subcommand given on the command line."""
    match sys.argv[1:]:
        case ["check", *paths] if paths:
            diagnostics = check(*paths)
            for diagnostic in diagnostics:
                sys.stdout.write(_render(diagnostic) + "\n")
            return 1 if any(d.is_blocking() for d in diagnostics) else 0
        case _:
            sys.stderr.write(_USAGE + "\n")
            return 2


if __name__ == "__main__":
    sys.exit(main())
