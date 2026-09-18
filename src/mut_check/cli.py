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

`Diagnostic.text` always carries color (both `ty`'s own, forced via
`--color=always` since its subprocess stdout is never a real terminal, and
`_reassignment`'s hand-applied match of that same style -- see `_ansi`'s
docstring). This is the one place that decides whether to actually *show*
it: real `ty check` picks color based on whether *its* stdout is a
terminal, and this emulates that same decision for `immut check`'s own
stdout, stripping otherwise (piped output, redirected to a file, CI logs).

`--untyped=<mode>` is a CLI-only flag for now (no `pyproject.toml` support
yet -- a natural future extension, since `ty` itself reads config from
`pyproject.toml`/`ty.toml`, but out of scope until this flag's shape has
proven itself).
"""

import sys

from mut_check import UntypedMode, check
from mut_check._ansi import strip_ansi

_USAGE = "usage: immut check [--untyped=strict|permissive|ignored] <path> [<path> ...]"

_UNTYPED_MODES: frozenset[UntypedMode] = frozenset({"strict", "permissive", "ignored"})


def _parse_untyped_mode(value: str) -> UntypedMode | None:
    if value in _UNTYPED_MODES:
        return value
    return None


def main() -> int:
    """Dispatch the `immut` subcommand given on the command line."""
    match sys.argv[1:]:
        case ["check", *rest] if rest:
            untyped: UntypedMode = "permissive"
            paths: list[str] = []
            for arg in rest:
                if arg.startswith("--untyped="):
                    parsed = _parse_untyped_mode(arg.removeprefix("--untyped="))
                    if parsed is None:
                        sys.stderr.write(_USAGE + "\n")
                        return 2
                    untyped = parsed
                else:
                    paths.append(arg)
            if not paths:
                sys.stderr.write(_USAGE + "\n")
                return 2

            diagnostics = check(*paths, untyped=untyped)
            if not diagnostics:
                sys.stdout.write("All checks passed!\n")
                return 0

            should_color = sys.stdout.isatty()
            texts = (d.text for d in diagnostics) if should_color else (strip_ansi(d.text) for d in diagnostics)
            sys.stdout.write("\n\n".join(texts))
            noun = "diagnostic" if len(diagnostics) == 1 else "diagnostics"
            sys.stdout.write(f"\n\nFound {len(diagnostics)} {noun}\n")
            return 1 if any(d.is_blocking() for d in diagnostics) else 0
        case _:
            sys.stderr.write(_USAGE + "\n")
            return 2


if __name__ == "__main__":
    sys.exit(main())
