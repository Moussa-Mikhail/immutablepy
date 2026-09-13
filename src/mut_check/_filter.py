"""
Suppress `ty`'s construction/literal false positive.

`ty` natively enforces `Mut[T] <: T`, but rejects the reverse -- a plain
value assigned where `Mut[T]` is expected -- because the value genuinely
lacks `MutMarker`. Per CLAUDE.md's construction exemption: an object created
in the current scope can be assigned/passed/returned as `Mut`, since it's
provably unaliased at that point -- nothing else could hold a reference to
it yet. `ty` has no notion of this, so this module corrects the diagnostics
after the fact: for each diagnostic on a `Mut[...]` target/parameter/return
type, check whether the *exact expression `ty` flagged* is one of these
"freshly created" node types, regardless of the syntactic role it plays
(assignment RHS, `return` value, call argument, ...) -- `ty` always points
its diagnostic at that expression's own position, so matching purely on
position generalizes across all three uniformly, with no need to handle
`AnnAssign`/`Return`/`Call` as separate cases:

- Literal displays: `ast.Constant`/`List`/`Dict`/`Set`/`Tuple`.
- Comprehensions/generator expressions -- the resulting container is a
  reference nothing else can have yet, by the same reasoning as a literal.
- Class-instantiation calls only, not arbitrary function calls. Instantiating
  a class has a *language-level* freshness guarantee (`__new__` always
  allocates, whatever `__init__` does with it) that an arbitrary function's
  return value simply doesn't have -- confirmed this distinction matters
  directly, not just in theory: an earlier version of this module treated
  *any* bare-name call as fresh, which meant inferring freshness for
  `get_values()` (an ordinary function) from its *implementation* (`return
  [1], [2]`, which happens to construct fresh lists) rather than from its
  *declared return type* (`tuple[list[int], list[int]]`, plain, no `Mut`
  anywhere) -- exactly the kind of body-inference this design's "no
  implicit inference from bodies" stance (see "Methods and per-field
  mutability" above) already rejects elsewhere, just not caught here until
  someone pointed out this fixture's premise didn't hold up. So only
  locally-`class`-defined names and the built-in mutable-container
  constructors (`list`, `dict`, `set`, `bytearray`) count -- not just any
  callable, and not method calls (`obj.method(...)`, i.e. `Call.func` is an
  `Attribute`): the call's own AST position coincides with the *receiver*
  `obj`'s position, not with anything the call itself returns. Confirmed
  this matters too -- `c.increment()` on a plain (non-`Mut`) receiver `c`,
  calling a method requiring `self: Mut[Self]`, produces a diagnostic at
  that same coinciding position; treating every `Call` as fresh incorrectly
  exempted it, since the receiver `c` is genuinely aliased and not fresh
  at all.

`for`/`with` target bindings (`for x in ...:`, `with ... as x:`) get the
same treatment for a different reason: per CLAUDE.md's "Pre-declaration for
loops, unpacking, and `with`", each iteration's/context's implicit binding
is itself a fresh event, not a reassignment needing permission, regardless
of the target's type -- this is sound because it changes nothing real: once
`x` is declared `Mut[T]`, `ty` already treats it as `Mut[T]` for the rest of
the scope regardless of whether this specific diagnostic is shown (confirmed
via `reveal_type`). Real enforcement of "does the iterable's element
actually carry `Mut`" is a different, not-yet-built question for the custom
pass, not something this diagnostic ever answered.

The message check only searches lines *not* nested under a `└──` tree
marker. Confirmed this matters too: a class with a plain field failing to
satisfy a `Mut`-declaring `Protocol` (see CLAUDE.md's "Protocols" section)
produces a diagnostic whose *only* `Mut[` mention is three levels deep in
such a tree (`Locked` incompatible with `HasValue` because member `value`
isn't `Mut`) -- a structural field-type mismatch that has nothing to do
with freshness, wrongly matched before this restriction (the outer call
`Locked()` is a bare-name call, so `_FRESH_NODES` alone didn't exclude it).

Not covered: a `Name` referring to a value obtained earlier (even from a
fresh call) -- only the call/literal/comprehension's *own* position is
exempt, not every later reference to whatever it produced; or subsequent
body mutations (`i += 1`) -- those are separate diagnostics at a different
location, judged independently.
"""

import ast
import re
from typing import TypeIs

from immutablepy import Mut
from mut_check._diagnostics import Diagnostic

_MUT_TARGET_MESSAGE = re.compile(r"(?:is not assignable to|[Ee]xpected) `Mut\[")
_NESTED_TREE_LINE = re.compile(r"└──")

_EXEMPT_CODES = frozenset({"invalid-assignment", "invalid-argument-type", "invalid-return-type"})

_FRESH_NODES = (
    ast.Constant,
    ast.List,
    ast.Dict,
    ast.Set,
    ast.Tuple,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)


# Built-in mutable-container constructors -- language-level fresh-allocation
# guarantee, same as a locally-defined class. Immutable ones aren't needed
# here: `_immutable` already exempts them by type name regardless of origin.
_BUILTIN_CONSTRUCTORS = frozenset({"list", "dict", "set", "bytearray"})


def _is_fresh(node: ast.AST, constructor_names: frozenset[str]) -> TypeIs[ast.expr]:
    if isinstance(node, _FRESH_NODES):
        return True
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in constructor_names


type _LocationsByFile = dict[str, set[tuple[int, int]]]


def _construction_exempt_locations(source: str) -> set[tuple[int, int]]:
    """
    Return `(line, col)` (1-indexed) of every construction-exempt position.

    Freshly created expressions (anywhere -- assignment, `return`, call
    argument, ...), and `for`/`with` target names.
    """
    tree = ast.parse(source)
    constructor_names = _BUILTIN_CONSTRUCTORS | {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }

    locations = set()
    for node in ast.walk(tree):
        if _is_fresh(node, constructor_names):
            locations.add((node.lineno, node.col_offset + 1))
        elif isinstance(node, ast.For | ast.AsyncFor) and isinstance(node.target, ast.Name):
            locations.add((node.target.lineno, node.target.col_offset + 1))
        elif isinstance(node, ast.With):
            for item in node.items:
                if isinstance(item.optional_vars, ast.Name):
                    locations.add((item.optional_vars.lineno, item.optional_vars.col_offset + 1))
    return locations


def _has_mut_target_message(text: str) -> bool:
    return any(
        _MUT_TARGET_MESSAGE.search(line) and not _NESTED_TREE_LINE.search(line) for line in text.splitlines()
    )


def _is_construction_exempt_false_positive(diagnostic: Diagnostic, locations_by_file: _LocationsByFile) -> bool:
    if diagnostic.code not in _EXEMPT_CODES:
        return False
    if not _has_mut_target_message(diagnostic.text):
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
