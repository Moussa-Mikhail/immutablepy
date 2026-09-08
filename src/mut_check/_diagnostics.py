"""
The structured diagnostic shape shared internally by `mut_check`.

`text` is `ty`'s own diagnostic block, verbatim -- this is what lets `immut
check`'s output look exactly like `ty check`'s: `mut_check` never re-renders
it, only decides (via `severity`/`code`/`file`/`line`/`col`) which blocks to
keep.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Diagnostic:
    """One diagnostic, parsed from `ty`'s default text output."""

    severity: str  # "error" | "warning" | "info"
    code: str
    file: Path
    line: int
    col: int
    text: str

    def is_blocking(self) -> bool:
        """Whether this diagnostic alone should make a check fail."""
        return self.severity in {"error", "warning"}
