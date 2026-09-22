"""
ANSI color handling shared across `mut_check`.

`ty` is invoked with `--color=always` (see `_ty.py`) so `Diagnostic.text`
always carries `ty`'s native color codes, regardless of whether stdout is a
terminal -- capturing via `subprocess.run` always looks like a non-tty to
`ty` itself, so the default `--color=auto` would silently produce plain
text every time. Deciding whether to actually *show* color is deferred to
`cli.py`, which knows the real output destination -- `strip_ansi` is how it
emulates `ty`'s own auto-detection when stdout isn't a terminal.

Color codes also land inside the message text itself (e.g. `]` and `:` on
the header line are separated by a reset/bold pair), which breaks naive
substring/regex matching against `Diagnostic.text` -- `_ty._parse` and the
`_filter`/`_immutable` exemption checks all match on a `strip_ansi`'d copy
for that reason, while keeping the original colored block for display.

As of `ty` 0.0.82, the header line also carries an OSC 8 terminal hyperlink
around the diagnostic code (an escape-bracket-8-semicolon-semicolon prefix,
the URL, then a matching close, wrapping the whole `[code]` token) even
under `--color=always` capture -- a second escape family, not just SGR color
codes. Left unstripped, it lands *inside* the `[code]` brackets `_ty._HEADER`
matches on, so every diagnostic silently failed to parse (confirmed:
`_ty.run` returned zero diagnostics against a fixture `ty` itself exits
nonzero on, both directly reproduced and caught by the test suite going
fully green on fixtures asserting real violations). See `_ANSI_RE`'s pattern
for the exact escape sequence matched.

`mut_check`'s own diagnostics (`_reassignment`) aren't rendered by `ty` at
all, so `_reassignment` builds its text with these same color constants
directly, matching `ty`'s style (bold-red header, bold-blue location/pipe
lines, bold-red pointer) so `immut check`'s output looks uniform regardless
of which pass produced a given diagnostic.
"""

import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m|\x1b\]8;;[^\x1b]*\x1b\\")

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
RED = "\x1b[91m"
BLUE = "\x1b[94m"


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences, for parsing/matching `ty`'s raw structure."""
    return _ANSI_RE.sub("", text)
