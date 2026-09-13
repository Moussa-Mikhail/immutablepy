"""
Suppress `ty`'s construction/literal false positive.

`ty` natively enforces `Mut[T] <: T`, but rejects the reverse -- a plain
value assigned where `Mut[T]` is expected -- because the value genuinely
lacks `MutMarker`. Per CLAUDE.md's construction exemption, a *fresh literal*
assigned directly to a `Mut[T]`-declared binding is provably unaliased and
must satisfy `Mut` anyway. `ty` has no notion of freshness, so this module
corrects the diagnostics after the fact: for each `invalid-assignment`
diagnostic on a `Mut[...]` target, check whether it's at a location this
module considers exempt, and drop it if so. Two categories:

- `AnnAssign` (`x: Mut[T] = <literal>`) whose value is a literal display
  (`ast.Constant`/`List`/`Dict`/`Set`/`Tuple`).
- `for`/`with` target bindings (`for x in ...:`, `with ... as x:`) where `x`
  is pre-declared `Mut[T]` -- per CLAUDE.md's "Pre-declaration for loops,
  unpacking, and `with`", each iteration's/context's implicit binding is
  itself a fresh event, not a reassignment needing permission, regardless of
  `T`. This is sound *because* it changes nothing real: once `x` is declared
  `Mut[T]`, `ty` already treats it as `Mut[T]` for the rest of the scope
  regardless of whether this specific diagnostic is shown (confirmed via
  `reveal_type` -- the declared type governs downstream, not the diagnostic
  outcome). Suppressing it removes a confusing false positive without
  loosening any enforcement that existed. Real enforcement of "does the
  iterable's element actually carry `Mut`" is a different, not-yet-built
  question for the custom pass, not something this diagnostic ever answered.

Not covered: unpacking (a different AST shape, and its diagnostics already
carry the `MutMarker` explanation `_immutable` can act on for immutable
types), or subsequent body mutations (`i += 1`) -- those are separate
diagnostics at a different location, judged independently.
"""

import ast
import re

from immutablepy import Mut
from mut_check._diagnostics import Diagnostic

_ASSIGNMENT_MESSAGE = re.compile(r"is not assignable to `Mut\[")

_LITERAL_NODES = (ast.Constant, ast.List, ast.Dict, ast.Set, ast.Tuple)

type _LocationsByFile = dict[str, set[tuple[int, int]]]


def _construction_exempt_locations(source: str) -> set[tuple[int, int]]:
    """
    Return `(line, col)` (1-indexed) of every construction-exempt binding.

    Literal `AnnAssign` values, and `for`/`with` target names.
    """
    tree = ast.parse(source)
    locations = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.value, _LITERAL_NODES):
            locations.add((node.value.lineno, node.value.col_offset + 1))
        elif isinstance(node, ast.For | ast.AsyncFor) and isinstance(node.target, ast.Name):
            locations.add((node.target.lineno, node.target.col_offset + 1))
        elif isinstance(node, ast.With):
            for item in node.items:
                if isinstance(item.optional_vars, ast.Name):
                    locations.add((item.optional_vars.lineno, item.optional_vars.col_offset + 1))
    return locations


def _is_construction_exempt_false_positive(diagnostic: Diagnostic, locations_by_file: _LocationsByFile) -> bool:
    if diagnostic.code != "invalid-assignment":
        return False
    if not _ASSIGNMENT_MESSAGE.search(diagnostic.text):
        return False
    locations = locations_by_file.get(str(diagnostic.file))
    return locations is not None and (diagnostic.line, diagnostic.col) in locations


def filter_construction_exemption(diagnostics: Mut[list[Diagnostic]]) -> Mut[list[Diagnostic]]:
    """Drop diagnostics that are exactly `ty`'s construction/literal false positive."""
    if not diagnostics:
        return diagnostics

    locations_by_file: _LocationsByFile = {}
    for diagnostic in diagnostics:
        file = str(diagnostic.file)
        if file not in locations_by_file:
            locations_by_file[file] = _construction_exempt_locations(diagnostic.file.read_text())

    return [d for d in diagnostics if not _is_construction_exempt_false_positive(d, locations_by_file)]
