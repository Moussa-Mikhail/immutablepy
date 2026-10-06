# Rust-Inspired Mutability System for Python — Project Rules

Capability-based mutability system for Python, inspired by Rust but not a port of it.
Targets conventional typed Python (no `getattr`/`setattr`/monkeypatching). Fully static
enforcement, no runtime checks.

**Philosophy**: personal project — fun, interesting, possibly useful. Where "looks and
feels right" conflicts with "broad compatibility," the former wins most of the time.

Rationale, rejected alternatives, and confirmation/testing trails for every rule below
live in `docs/decisions.md` — read it before proposing a design change, so you don't
re-litigate something already settled.

## Core model

- `Mut[T]` = permission to mutate. Unannotated `T` = implicitly read-only.
- Single axis: `Mut[T] <: T`. No finer sub-permission tiers.
- `Mut` is transitive: required to mutate anything reachable at any depth, no per-field
  override, no field-scoped grants.
- Fields inherit mutability from their owner: through a `Mut` owner (including `self` in
  a `Mut[Self]`/`@mut` method) a field is writable/mutable; through a read-only owner it
  is read-only. There are no locked fields.
- No *type* defaults to `Mut` — not `list`/`dict`/`set`, not `Mutable*` ABCs. Always
  explicit on locals, parameters and returns; a field's mutability comes from its owner.

## Rules

### Locals and reassignment
Unannotated local `T` is read-only; reassignment (plain or augmented) requires `Mut[T]`
on the declaration. A local's *first* real assignment is always free. Parameters have
no free first assignment. `for`/`with`/unpacking target bindings establish/preserve
status but a subsequent reassignment inside the body is checked. Enforced by
`mut_check._reassignment`, `ast.Name` targets only — attribute writes are a separate,
not-yet-designed rule (a write requires `Mut` on the owner).

### Immutable types always satisfy `Mut[T]`
Any value of an immutable type — `int`, `str`, `bytes`, `float`, `bool`, `complex`,
`frozenset`, `tuple`, and structurally read-only types with no mutating members
(`Sequence[T]`, `Mapping[K, V]`, `Iterable[T]`, `Iterator[T]`, `Container[T]`, `Sized`,
`Hashable`, `Reversible`, the `*View` types, ...) — satisfies a `Mut[T]` position
unconditionally, regardless of origin. `MutableSequence`/`MutableMapping`/`MutableSet`
stay excluded, same as `list`/`dict`/`set`. Hand-maintained allowlist, not derived from
structure. This does not change the local-reassignment rule above — only the "does a
value satisfy a `Mut` position" direction.

### Constructors and literals satisfy `Mut` positions
A value with no prior type commitment — a literal, comprehension/generator expression,
or a class-instantiation call (not an arbitrary function call, not a method call) — can
be assigned/passed/returned as `Mut` at its point of construction. A `Name` reference
is never exempt; its type was already fixed by its declaration.

### Pre-declaration for `for`/`with`/unpacking
No post-assignment annotation (`ty` rejects it). Pre-declare the binding's type, then
assign:
```python
i: Mut[int]
for i in range(5): ...       # i is Mut[int] per the pre-declaration

a: Mut[int]
b: int
a, b = pair                  # unpacking into pre-declared bindings

f: Mut[io.StringIO]
with io.StringIO() as f: ... # f is Mut per the pre-declaration
```
For loops: pre-declaring `Mut[T]` is only required if the loop body reassigns/mutates
the target. A read-only loop needs no `Mut` at all. Unpacking without pre-declaration
produces immutable bindings by default.

### Comprehensions are exempt
Comprehension variables are scoped to the comprehension — no annotation can reach them.
Mutation permission for a comprehension's iteration variable is derived from the source
iterable's element type by the custom AST pass, not from an annotation on the variable.

### Container content mutability is compositional
`Mut[list[User]]` (can restructure the list, can't mutate elements) and
`Mut[list[Mut[User]]]` (can do both) are genuinely different permissions — matches
Rust's `&mut Vec<&T>` vs `&mut Vec<&mut T>`.

### Methods and per-field mutability
- `Mut[Self]` marks mutating methods. For mypy (which hard-errors on this): use the
  `@mut` decorator, not per-line/project-wide suppression.
- No implicit inference of mutability from method bodies — ever.
- Fields have no mutability of their own: writing or mutating `o.field` (including
  `self.field` in a method) requires `Mut` on `o`. A field annotation needs no outer
  `Mut` (one is redundant but allowed); `Mut` nested in type arguments (`list[Mut[User]]`) stays explicit, per
  "Container content mutability is compositional".
- To make a field unchangeable, use what Python already has, enforced by every checker:
  `typing.Final` (no rebinding, even from the class's own methods), a read-only
  `@property`, or an immutable/read-only field type (`tuple`, `frozenset`, `Sequence`,
  `Mapping`). `mut_check` adds no lock of its own.
- Constructors (`__init__`, `__post_init__`, `__new__`, classmethod constructors) must be
  able to write the new object's fields — mechanism not yet designed (likely an implicit
  `Mut` on the object under construction). Nothing is locked afterward, so no escape
  check is needed.

### Protocols
No locked fields means no class can disagree with a protocol about a field's
mutability; whether a protocol attribute is settable is Python's own rule, enforced by
every checker (a read-only `@property` or `Final` attribute fails a settable protocol
attribute). Mutation permission comes from the reference (`Mut[P]`), like any type.
Remaining gap: unanalyzed third-party/untyped code.

## Implementation architecture (summary)

- Tool ships its own pinned, private `ty` binary, invoked via LSP.
- The private `ty` instance resolves `Mut[T]` to a real `Intersection[T, MutMarker]`
  type internally. Users' own type checkers see the plain transparent definition
  (`type Mut[T] = T`) — zero config, zero breakage for them.
- Hybrid enforcement: `ty`'s native `Mut[T] <: T` checking, plus a custom filter
  (`mut_check._filter`, `mut_check._immutable`) that suppresses `ty`'s
  false-positive "plain `T` not assignable to `Mut[T]`" diagnostics at construction
  sites, and a custom pass that owns transitivity/reachability and constructor writes
  (not type-compatibility concerns `ty` can check).
- Stdlib/third-party support: only genuinely mutable stdlib types (`list`, `dict`,
  `set`, `bytearray`, ...) need stubbing, via a vendored `stubs/typeshed` fork pointed
  to by `ty.toml`'s `typeshed` setting (replaces `ty`'s embedded default entirely, not
  an `extra-paths` overlay), with `Mut`-aware signatures for the mutating methods.
  AST-filter fallback remains viable.

**Target audience**: developers who prefer functional-style programming and want
strict static guarantees — stricter than most Python developers will tolerate.

## Incremental adoption

Mypy-style scope-level opt-in: a function/file/module with zero `Mut` annotations is
skipped entirely by the checker; any `Mut` annotation makes the scope fully checked.
Adding `Mut` to one function doesn't require adding it to every other function
touching the same values. Each function/lambda/module scope is gated independently.
`ClassDef` and comprehension scopes are not gated by this ratchet.

## Untyped-code handling

Three-mode knob on `mut_check`'s custom passes only (`ty` itself has no equivalent),
default `"permissive"`:
- **`permissive`** (default): the incremental-adoption ratchet above.
- **`strict`**: ratchet disabled — every scope checked regardless of annotations.
- **`ignored`**: file-level cut — a file with zero type annotations of any kind is
  never parsed for a custom pass at all.

CLI-only today: `immut check --untyped=<mode>`. No config-file support yet
(deliberately deferred).

## Open

- Constructor writes: how a constructor gets write permission on the object it's
  building (likely an implicit `Mut` on `self`). Needs design.
- Full backend integration: architecture decided and validated, not yet built.
- Stdlib stubs: scope and initial coverage not yet determined.
- Untyped-code handling config file: `pyproject.toml`/`ty.toml`-style support for the
  `untyped` mode, on top of today's CLI-only flag.
- Augmented assignment (`total += i`) on a *mutable* type with a custom `__iadd__`
  returning a fresh, unmarked value: open gap, no fixture yet.
- Field-access typing: `type_of(o.field)` inherits `o`'s `Mut`-ness for the outer level
  (`Mut[declared]` through a `Mut` owner, plain `declared` through a read-only one),
  nested `Mut` untouched. Proposed, not designed or built — see decisions.md's "Fields
  inherit mutability from the owner".
