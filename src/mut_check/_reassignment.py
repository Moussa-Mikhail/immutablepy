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
    Name,
    NodeVisitor,
    SetComp,
    Subscript,
    Tuple,
    With,
    arguments,
    expr,
    parse,
)
from pathlib import Path
from typing import override

from mut_check._ansi import BLUE, BOLD, RED, RESET
from mut_check._diagnostics import Diagnostic

_CODE = "reassignment-without-mut"


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
    def __init__(self) -> None:
        self.violations: list[Name] = []
        self._scope = _Scope()
        self._scope_stack: list[_Scope] = []

    def _push_scope(self, scope: _Scope | None = None) -> None:
        self._scope_stack.append(self._scope)
        self._scope = scope if scope is not None else _Scope()

    def _pop_scope(self) -> None:
        self._scope = self._scope_stack.pop()

    def _visit_function_like(self, node: FunctionDef | AsyncFunctionDef | Lambda) -> None:
        self._push_scope(_param_scope(node.args))
        self.generic_visit(node)
        self._pop_scope()

    @override
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        self._visit_function_like(node)

    @override
    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> None:
        self._visit_function_like(node)

    @override
    def visit_Lambda(self, node: Lambda) -> None:
        self._visit_function_like(node)

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

    def _check_and_bind(self, name_node: Name) -> None:
        name = name_node.id
        if name in self._scope.bound:
            if not self._scope.permission.get(name, False):
                self.violations.append(name_node)
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
                self.violations.append(node.target)
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


def _render(file: Path, target: Name, source_lines: list[str]) -> str:
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

    The left gutter's width tracks the line number's own width (confirmed
    against real `ty` output: a 2-digit line number widens the `|` column by
    one space on every line, not just the numbered one) -- a fixed-width
    gutter misaligns the `|` column as soon as a fixture's line number goes
    multi-digit.
    """
    line, col = target.lineno, target.col_offset + 1
    source_line = source_lines[line - 1] if line - 1 < len(source_lines) else ""
    gutter = " " * len(str(line))
    indent = " " * (col - 1)
    return (
        f"{BOLD}{RED}error[{_CODE}]{RESET}{BOLD}: `{target.id}` is reassigned without a `Mut[...]` declaration{RESET}\n"
        f"{gutter}{BOLD}{BLUE}--> {RESET}{file}:{line}:{col}\n"
        f"{gutter} {BOLD}{BLUE}|{RESET}\n"
        f"{BOLD}{BLUE}{line} |{RESET} {source_line}\n"
        f"{gutter} {BOLD}{BLUE}|{RESET} {indent}{BOLD}{RED}^{RESET}"
    )


def find_unpermitted_reassignments(path: Path) -> list[Diagnostic]:
    """Find `Name` targets reassigned without a `Mut[...]` declaration in `path`."""
    source = path.read_text()
    checker = _ReassignmentChecker()
    checker.visit(parse(source))
    if not checker.violations:
        return []

    source_lines = source.splitlines()
    return [
        Diagnostic(
            severity="error",
            code=_CODE,
            file=path,
            line=target.lineno,
            col=target.col_offset + 1,
            text=_render(path, target, source_lines),
        )
        for target in checker.violations
    ]
