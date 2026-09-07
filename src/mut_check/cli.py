"""
Command-line entry point for the `immut` script.

Uses an explicit `check` subcommand, matching `ruff check`/`ty check`, since
CLAUDE.md already commits to a second, fundamentally different mode later
(driving the bundled `ty` via LSP instead of one-shot invocation) -- the
same relationship as `ty check` vs `ty server`. Making `check` explicit now
avoids a breaking change to add that second mode later.
"""

import sys

from mut_check import check as run_check

_USAGE = "usage: immut check <path> [<path> ...]"


def main() -> int:
    """Dispatch the `immut` subcommand given on the command line."""
    match sys.argv[1:]:
        case ["check", *paths] if paths:
            result = run_check(*paths)
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            return result.returncode
        case _:
            sys.stderr.write(_USAGE + "\n")
            return 2


if __name__ == "__main__":
    sys.exit(main())
