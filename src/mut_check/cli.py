"""
Command-line entry point for the `immut` script.

Uses an explicit `check` subcommand, matching `ruff check`/`ty check`, since
CLAUDE.md already commits to a second, fundamentally different mode later
(driving the bundled `ty` via LSP instead of one-shot invocation) -- the
same relationship as `ty check` vs `ty server`. Making `check` explicit now
avoids a breaking change to add that second mode later.

Prints `mut_check.check`'s surviving diagnostics using `ty`'s own verbatim
text (`Diagnostic.text`), plus a matching trailer, so `immut check`'s output
looks exactly like `ty check`'s -- filtered false positives just aren't there.
"""

import sys

from mut_check import check

_USAGE = "usage: immut check <path> [<path> ...]"


def main() -> int:
    """Dispatch the `immut` subcommand given on the command line."""
    match sys.argv[1:]:
        case ["check", *paths] if paths:
            diagnostics = check(*paths)
            if not diagnostics:
                sys.stdout.write("All checks passed!\n")
                return 0
            noun = "diagnostic" if len(diagnostics) == 1 else "diagnostics"
            sys.stdout.write("\n\n".join(d.text for d in diagnostics))
            sys.stdout.write(f"\n\nFound {len(diagnostics)} {noun}\n")
            return 1 if any(d.is_blocking() for d in diagnostics) else 0
        case _:
            sys.stderr.write(_USAGE + "\n")
            return 2


if __name__ == "__main__":
    sys.exit(main())
