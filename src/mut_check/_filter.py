"""
Suppress `ty`'s construction/literal false positive.

`ty` natively enforces `Mut[T] <: T`, but rejects the reverse -- a plain
value assigned where `Mut[T]` is expected -- because the value genuinely
lacks `MutMarker`. Per CLAUDE.md's construction exemption, a *fresh literal*
assigned directly to a `Mut[T]`-declared binding is provably unaliased and
must satisfy `Mut` anyway. `ty` has no notion of freshness, so this module
corrects the diagnostics after the fact: for each `invalid-assignment`
diagnostic on a `Mut[...]` target, check whether the assignment's own source
at that exact location is a literal display (`ast.Constant`/`List`/`Dict`/
`Set`/`Tuple`) and drop the diagnostic if so.

Scoped deliberately narrow: only `AnnAssign` (`x: Mut[T] = <literal>`), not
constructor calls, for-loop/`with` pre-declared targets, or unpacking -- see
CLAUDE.md's "Hybrid enforcement" note on the message-shape gap for those.
Real errors (aliased values, genuine type mismatches) pass through
unmodified: their diagnostic code, message shape, or AST position never
match this filter's criteria.
"""

import ast
import re

from mut_check._diagnostics import Diagnostic

_ASSIGNMENT_MESSAGE = re.compile(r"is not assignable to `Mut\[")

_LITERAL_NODES = (ast.Constant, ast.List, ast.Dict, ast.Set, ast.Tuple)

type _LocationsByFile = dict[str, set[tuple[int, int]]]


def _literal_assignment_locations(source: str) -> set[tuple[int, int]]:
    """Return `(line, col)` (1-indexed) of every literal `AnnAssign` value."""
    tree = ast.parse(source)
    locations = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.value, _LITERAL_NODES):
            locations.add((node.value.lineno, node.value.col_offset + 1))
    return locations


def _is_literal_assignment_false_positive(diagnostic: Diagnostic, literal_locations: _LocationsByFile) -> bool:
    if diagnostic.code != "invalid-assignment":
        return False
    if not _ASSIGNMENT_MESSAGE.search(diagnostic.message):
        return False
    locations = literal_locations.get(str(diagnostic.file))
    return locations is not None and (diagnostic.line, diagnostic.col) in locations


def filter_construction_exemption(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    """Drop diagnostics that are exactly `ty`'s literal-construction false positive."""
    if not diagnostics:
        return diagnostics

    literal_locations: _LocationsByFile = {}
    for diagnostic in diagnostics:
        file = str(diagnostic.file)
        if file not in literal_locations:
            literal_locations[file] = _literal_assignment_locations(diagnostic.file.read_text())

    return [d for d in diagnostics if not _is_literal_assignment_false_positive(d, literal_locations)]
