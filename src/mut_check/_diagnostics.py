"""
The structured diagnostic shape shared by every `mut_check` frontend.

Both the CLI and the future LSP server (see CLAUDE.md's "Private ty backend")
need to present the same underlying results -- one as human-readable text,
the other as `publishDiagnostics` JSON. Neither should work from raw `ty`
text output directly, so `mut_check.check()` returns this structured form
instead, and each frontend renders it however fits.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Diagnostic:
    """One diagnostic, already decoded from `ty`'s `--output-format github` shape."""

    severity: str  # "error" | "warning" | "notice"
    code: str
    file: Path
    line: int
    col: int
    message: str

    def is_blocking(self) -> bool:
        """Whether this diagnostic alone should make a check fail."""
        return self.severity in {"error", "warning"}
