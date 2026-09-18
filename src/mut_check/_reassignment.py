"""
Custom check: reassigning a plain (non-`Mut`) local without permission.

Per CLAUDE.md's "Locals require `Mut` for reassignment": an unannotated
local is read-only, so a *second* assignment (or any augmented assignment,
which always presupposes an existing value) to a name not declared `Mut[T]`
is a violation. `ty` has no notion of this at all -- confirmed directly,
`for i in range(5): i += 1` with no `Mut` anywhere produces zero
diagnostics. This module is the first piece of the not-yet-built custom
pass (per CLAUDE.md's "Open" items): its diagnostics don't come from `ty`.

Scoped to `Name` targets only -- `self.attr = x` is an `Attribute`
target, a separate, not-yet-designed rule (per-field locks/construction
escape), not this one.

Gated by CLAUDE.md's "Incremental adoption" ratchet: a function/module scope
with zero `Mut` annotations of its own is skipped entirely by default (mode
`"permissive"`) -- confirmed this applies to this pass too, not just `ty`'s
intersection-type checking, even though every one of this module's own
"violation" fixtures originally had no `Mut` anywhere (they've since been
given a throwaway opt-in annotation to keep demonstrating the rule under the
new default). `"strict"` mode disables the gate, checking every scope
regardless of annotations -- today's behavior before this ratchet existed.
`"ignored"` mode adds a coarser, file-level cut on top: a file with zero
type annotations of *any* kind (not just `Mut`) is never even parsed for
this pass. `"ignored"` and `"permissive"` currently produce identical
diagnostics for a fully-untyped file (zero annotations anywhere trivially
means zero `Mut` annotations everywhere, so the per-scope gate already
empties it out) -- the only difference today is whether the file's AST is
walked at all, not what's reported. `ty` itself has no equivalent to any of
this: `ty check --help` exposes no strict/untyped-body flag at all, gradual
typing is unconditional there.

Tracking model: a scope stack, pushed/popped on function/lambda/class/
comprehension boundaries (matching real Python scoping -- assignment inside
a nested function creates a new local there unless `global`/`nonlocal` is
used, which this doesn't model; a plain `Assign`/`AugAssign` to such an
unmodeled name is conservatively not flagged, favoring false negatives over
false positives for a first pass). Each scope tracks two separate things,
deliberately not conflated:

- *Permission* (`name -> is_mut`): set by an `AnnAssign`'s annotation,
  whether or not it has a value -- a bare `x: list[int]` (no value) is a
  pure declaration, establishing permission for whenever the real
  assignment happens later.
- *Boundness* (which names have already received a real value): set by an
  `AnnAssign` *with* a value, a plain `Assign`, or a `for`/`with`/unpacking
  target binding. Only a name that's already bound can be "reassigned" --
  conflating this with permission was an earlier bug here: `b: list[int]`
  (bare) followed by `a, b = get_values()` looked like a second assignment
  to `b`, when it's really the first.

Parameters are pre-bound at function entry (from their annotation) -- no
free first assignment, since the call itself already bound them. A local's
first real assignment establishes its boundness (defaulting permission to
non-`Mut` if no prior declaration set it) and is never itself a violation.
`for`/`with`/unpacking target bindings establish boundness the same way and
are also never themselves a violation -- matching the exemption
`mut_check._filter` already gives the corresponding `ty` diagnostics --
only a *subsequent* reassignment/augmented-assignment is checked.
"""

from ast import (
    AST,
    AnnAssign,
    Assign,
    AsyncFor,
    AsyncFunctionDef,
    AsyncWith,
    AugAssign,
    ClassDef,
    DictComp,
    For,
    FunctionDef,
    GeneratorExp,
    Lambda,
    List,
    ListComp,
    Module,
    Name,
    NodeVisitor,
    SetComp,
    Subscript,
    Tuple,
    With,
    arguments,
    expr,
    parse,
    stmt,
    walk,
)
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, override

from mut_check._ansi import BLUE, BOLD, RED, RESET
from mut_check._diagnostics import Diagnostic

_CODE = "reassignment-without-mut"

type UntypedMode = Literal["strict", "permissive", "ignored"]

# Not `Lambda`: its body is always a single `expr`, so it can never contain
# the `Assign`/`AugAssign`/`AnnAssign`/`For`/`With` statements this checker
# flags violations on -- there's nothing for a per-lambda gate to ever apply
# to (confirmed: lambda parameters can't be annotated at all either --
# `lambda x: int: x` is a `SyntaxError` -- so a lambda's own scope can never
# even opt itself in).
_GatingScope = Module | FunctionDef | AsyncFunctionDef


def _is_mut_annotation(annotation: expr) -> bool:
    return (
        isinstance(annotation, Subscript)
        and isinstance(annotation.value, Name)
        and annotation.value.id == "Mut"
    )


def _flatten_name_targets(target: expr) -> list[Name]:
    """
    Flatten unpacking targets: `a, (b, c)` -> `[a, b, c]`.

    Ignores `Attribute`/`Subscript`/`Starred` targets -- out of scope for this check.
    """
    if isinstance(target, Name):
        return [target]
    if isinstance(target, Tuple | List):
        names = []
        for elt in target.elts:
            names.extend(_flatten_name_targets(elt))
        return names
    return []


# Not `Lambda`: it's an `expr`, never a member of a `stmt` sequence, so it
# can never appear in the `stmts` this tuple is matched against below.
_SCOPE_BOUNDARY_TYPES = (FunctionDef, AsyncFunctionDef, ClassDef)
_COMPOUND_STMT_FIELDS = ("body", "orelse", "finalbody")


def _own_scope_stmts(stmts: Sequence[stmt]) -> Iterator[stmt]:
    """Yield every statement in `stmts` belonging to this same scope, not descending into nested scopes."""
    for node in stmts:
        yield node
        if isinstance(node, _SCOPE_BOUNDARY_TYPES):
            continue
        for field in _COMPOUND_STMT_FIELDS:
            child_stmts = getattr(node, field, None)
            if child_stmts:
                yield from _own_scope_stmts(child_stmts)
        for handler in getattr(node, "handlers", ()):
            yield from _own_scope_stmts(handler.body)


def _has_own_mut_annotation(body: Sequence[stmt], args: arguments | None) -> bool:
    """Whether this scope declares `Mut[...]` on a parameter or an `AnnAssign` of its own."""
    if args is not None and any(
        arg.annotation is not None and _is_mut_annotation(arg.annotation)
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)
    ):
        return True
    return any(isinstance(node, AnnAssign) and _is_mut_annotation(node.annotation) for node in _own_scope_stmts(body))


def _relevant_scope_nodes(tree: Module) -> Iterator[_GatingScope]:
    """Yield `tree` itself plus every `FunctionDef`/`AsyncFunctionDef` -- the scopes the ratchet gates."""
    yield tree
    for node in walk(tree):
        if isinstance(node, FunctionDef | AsyncFunctionDef):
            yield node


def _compute_scope_has_mut(tree: Module) -> set[int]:
    """`id(scope_node)` for every scope with a `Mut` annotation of its own (see `_has_own_mut_annotation`)."""
    result: set[int] = set()
    for scope_node in _relevant_scope_nodes(tree):
        args = None if isinstance(scope_node, Module) else scope_node.args
        if _has_own_mut_annotation(scope_node.body, args):
            result.add(id(scope_node))
    return result


def _file_has_any_annotation(tree: Module) -> bool:
    """
    Whether `tree` has a type annotation of *any* kind anywhere -- not just `Mut` (see `"ignored"` mode).

    Lambda parameters can never be annotated at all (confirmed: `lambda x:
    int: x` is a `SyntaxError`), so lambdas are skipped -- they can never
    contribute a `True` here.
    """
    for node in walk(tree):
        if isinstance(node, AnnAssign):
            return True
        if isinstance(node, FunctionDef | AsyncFunctionDef):
            if node.returns is not None:
                return True
            args = node.args
            if any(arg.annotation is not None for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)):
                return True
    return False


class _Scope:
    def __init__(self) -> None:
        self.permission: dict[str, bool] = {}
        self.bound: set[str] = set()


def _param_scope(args: arguments) -> _Scope:
    scope = _Scope()
    for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
        is_mut = arg.annotation is not None and _is_mut_annotation(arg.annotation)
        scope.permission[arg.arg] = is_mut
        scope.bound.add(arg.arg)
    for vararg in (args.vararg, args.kwarg):
        if vararg is not None:
            scope.permission[vararg.arg] = False
            scope.bound.add(vararg.arg)
    return scope


class _ReassignmentChecker(NodeVisitor):
    def __init__(self, tree: Module) -> None:
        self.violations: list[tuple[Name, _GatingScope]] = []
        self._scope = _Scope()
        self._scope_stack: list[_Scope] = []
        self._gating_scope: _GatingScope = tree

    def _push_scope(self, scope: _Scope | None = None) -> None:
        self._scope_stack.append(self._scope)
        self._scope = scope if scope is not None else _Scope()

    def _pop_scope(self) -> None:
        self._scope = self._scope_stack.pop()

    def _visit_gated_function_like(self, node: FunctionDef | AsyncFunctionDef) -> None:
        self._push_scope(_param_scope(node.args))
        enclosing_gating_scope = self._gating_scope
        self._gating_scope = node
        self.generic_visit(node)
        self._gating_scope = enclosing_gating_scope
        self._pop_scope()

    @override
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        self._visit_gated_function_like(node)

    @override
    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> None:
        self._visit_gated_function_like(node)

    @override
    def visit_Lambda(self, node: Lambda) -> None:
        # No gating scope here (unlike `_visit_gated_function_like`): a lambda
        # body is always a single `expr`, so it can never contain the
        # statements this checker flags violations on -- see `_GatingScope`'s
        # comment for why there's nothing to gate.
        self._push_scope(_param_scope(node.args))
        self.generic_visit(node)
        self._pop_scope()

    def _scoped_generic_visit(self, node: AST) -> None:
        self._push_scope()
        self.generic_visit(node)
        self._pop_scope()

    @override
    def visit_ClassDef(self, node: ClassDef) -> None:
        self._scoped_generic_visit(node)

    @override
    def visit_ListComp(self, node: ListComp) -> None:
        self._scoped_generic_visit(node)

    @override
    def visit_SetComp(self, node: SetComp) -> None:
        self._scoped_generic_visit(node)

    @override
    def visit_DictComp(self, node: DictComp) -> None:
        self._scoped_generic_visit(node)

    @override
    def visit_GeneratorExp(self, node: GeneratorExp) -> None:
        self._scoped_generic_visit(node)

    def _record_violation(self, name_node: Name) -> None:
        self.violations.append((name_node, self._gating_scope))

    def _check_and_bind(self, name_node: Name) -> None:
        name = name_node.id
        if name in self._scope.bound:
            if not self._scope.permission.get(name, False):
                self._record_violation(name_node)
        else:
            self._scope.permission.setdefault(name, False)
            self._scope.bound.add(name)

    @override
    def visit_AnnAssign(self, node: AnnAssign) -> None:
        if isinstance(node.target, Name):
            name = node.target.id
            self._scope.permission[name] = _is_mut_annotation(node.annotation)
            if node.value is not None:
                self._check_and_bind(node.target)
        self.generic_visit(node)

    @override
    def visit_Assign(self, node: Assign) -> None:
        for top_target in node.targets:
            for name_node in _flatten_name_targets(top_target):
                self._check_and_bind(name_node)
        self.generic_visit(node)

    @override
    def visit_AugAssign(self, node: AugAssign) -> None:
        if isinstance(node.target, Name):
            name = node.target.id
            if name in self._scope.bound and not self._scope.permission.get(name, False):
                self._record_violation(node.target)
        self.generic_visit(node)

    def _handle_binding_target(self, target: expr) -> None:
        for name_node in _flatten_name_targets(target):
            name = name_node.id
            self._scope.permission.setdefault(name, False)
            self._scope.bound.add(name)

    def _visit_for(self, node: For | AsyncFor) -> None:
        self._handle_binding_target(node.target)
        self.generic_visit(node)

    @override
    def visit_For(self, node: For) -> None:
        self._visit_for(node)

    @override
    def visit_AsyncFor(self, node: AsyncFor) -> None:
        self._visit_for(node)

    def _visit_with(self, node: With | AsyncWith) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._handle_binding_target(item.optional_vars)
        self.generic_visit(node)

    @override
    def visit_With(self, node: With) -> None:
        self._visit_with(node)

    @override
    def visit_AsyncWith(self, node: AsyncWith) -> None:
        self._visit_with(node)


@dataclass(frozen=True)
class _Violation:
    file: Path
    target: Name
    source_lines: list[str]


def _find_violations(path: Path, mode: UntypedMode) -> list[_Violation]:
    source = path.read_text()
    tree = parse(source)
    if mode == "ignored" and not _file_has_any_annotation(tree):
        return []

    checker = _ReassignmentChecker(tree)
    checker.visit(tree)
    if not checker.violations:
        return []

    scopes_with_mut = _compute_scope_has_mut(tree) if mode != "strict" else set()
    source_lines = source.splitlines()
    return [
        _Violation(path, target, source_lines)
        for target, scope in checker.violations
        if mode == "strict" or id(scope) in scopes_with_mut
    ]


def _render(violation: _Violation, gutter_width: int) -> str:
    """
    Render this diagnostic in `ty`'s own colored style.

    This pass has no `ty` output to inherit color from (per this module's
    docstring, its diagnostics don't come from `ty` at all), so it applies
    `ty`'s own color scheme directly -- bold-red header, bold-blue location/
    pipe lines, bold-red pointer -- matching `--color=always` `ty` output
    byte-for-byte in style (confirmed against real `ty` diagnostics), so
    `immut check`'s output looks uniform regardless of which pass produced a
    given diagnostic. `cli.py` strips this the same way it strips `ty`'s own
    color when stdout isn't a terminal.

    `gutter_width` is shared across every reassignment diagnostic in one
    `check()` run (see `find_unpermitted_reassignments`), not derived from
    this violation's own line number -- unlike real `ty`, which sizes each
    diagnostic's gutter independently per its own line (confirmed: a
    diagnostic spanning lines 120 and 9 uses width 3 for one location block
    and width 1 for the other). That's fine for a single `ty`-rendered
    diagnostic, but left every one of *our* diagnostics a different width
    depending on which line it happened to land on, which read as visually
    inconsistent stacked together in one `immut check` run -- forcing one
    shared width (at least as wide as the widest line number, so nothing is
    truncated) makes them line up instead.
    """
    line, col = violation.target.lineno, violation.target.col_offset + 1
    source_line = violation.source_lines[line - 1] if line - 1 < len(violation.source_lines) else ""
    gutter = " " * gutter_width
    line_str = str(line).rjust(gutter_width)
    indent = " " * (col - 1)
    header = f"`{violation.target.id}` is reassigned without a `Mut[...]` declaration"
    return (
        f"{BOLD}{RED}error[{_CODE}]{RESET}{BOLD}: {header}{RESET}\n"
        f"{gutter}{BOLD}{BLUE}--> {RESET}{violation.file}:{line}:{col}\n"
        f"{gutter} {BOLD}{BLUE}|{RESET}\n"
        f"{BOLD}{BLUE}{line_str} |{RESET} {source_line}\n"
        f"{gutter} {BOLD}{BLUE}|{RESET} {indent}{BOLD}{RED}^{RESET}"
    )


def find_unpermitted_reassignments(*paths: Path, mode: UntypedMode = "permissive") -> list[Diagnostic]:
    """
    Find `Name` targets reassigned without a `Mut[...]` declaration across `paths`.

    `mode` is this module's docstring's "Incremental adoption" ratchet knob
    (`"strict"`/`"permissive"`/`"ignored"`) -- see `_find_violations` and
    `_has_own_mut_annotation` for what each mode actually gates.

    All violations found across every path share one gutter width (the
    widest line number among them) -- see `_render`'s docstring for why
    that's a deliberate departure from real `ty`'s per-diagnostic sizing.
    """
    violations = [violation for path in paths for violation in _find_violations(path, mode)]
    if not violations:
        return []

    gutter_width = max(len(str(violation.target.lineno)) for violation in violations)
    return [
        Diagnostic(
            severity="error",
            code=_CODE,
            file=violation.file,
            line=violation.target.lineno,
            col=violation.target.col_offset + 1,
            text=_render(violation, gutter_width),
        )
        for violation in violations
    ]
