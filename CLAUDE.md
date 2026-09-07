# Rust-Inspired Mutability System for Python — Decision Log

Capability-based mutability system for Python, inspired by Rust but not a port of it.
Targets conventional typed Python (no `getattr`/`setattr`/monkeypatching). Fully static
enforcement, no runtime checks.

**Philosophy**: personal project — fun, interesting, possibly useful. Where "looks and
feels right" conflicts with "broad compatibility," the former wins most of the time.

## Core model

- `Mut[T]` = permission to mutate. Unannotated `T` = implicitly read-only.
- Lattice: `Mut[T] <: T`. Single axis — Pony's 6-tier system was reviewed and rejected
  (its extra tiers need whole-program alias analysis, infeasible in Python). Finer
  granularity within `Mut` (insert/remove/overwrite sub-permissions) also declined.

## Rejected: type-broadening lint

Suggesting `list[T]` → `Sequence[T]` when a parameter is never mutated: rejected. If
the function later needs mutation, walking back costs two edits versus one — the lint
would be making a speculative bet on the user's behalf.

## No type defaults to `Mut`, ever

`list`/`dict`/`set`: rejected (habit, not signal). `MutableSequence`/`MutableMapping`/
`MutableSet`: also rejected — counterexample: `s = o.mutset` where `o` isn't `Mut`. The
type carries no memory of origin, so defaulting by type alone leaks permission through
the transitivity boundary. `Mutable*` ABCs remain the recommended spelling over concrete
types, just always explicitly `Mut`-wrapped.

## Transitivity of `Mut` — kept, no override

`Mut[T]` required to mutate anything reachable at any depth. Without it, a permission
check at a function boundary is bypassable via any attribute chain — the check becomes
theater. Cost accepted: permission virality (same class as Rust's `&mut` propagation)
and no field-scoped grants. A per-field override (letting a class cap transitivity) was
rejected — Rust's answer to this is module-privacy, which Python already has.

## Protocols

Structural conformance under `Annotated`-based erasure is blind to `Mut` tags — a class
can declare a field locked while a protocol it satisfies claims `Mut`, with nothing
catching the mismatch (confirmed directly). **Resolved by the intersection-type
approach** (below): `ty`'s own protocol-conformance checking catches this natively once
protocol members use real intersection-typed `Mut`. Usage-driven (fires at real call
sites), not exhaustive N×M. Remaining gap: unanalyzed third-party code — the general
untyped-code limitation, not Protocol-specific.

Note: Python's `Protocol` works with zero textual relationship between class and
protocol — no import, no inheritance, no reference at all (confirmed against `typing`
docs). Relevant because any custom verification would need real pairwise structural
comparison, not reference-following — but since `ty` handles this natively now, that
cost is avoided entirely.

## Methods and per-field mutability

- **`Mut[Self]`** is the default way to mark mutating methods. mypy hard-errors on this
  (bug report filed; bare `self: Self` is accepted, wrapping `Self` in *any* generic
  alias triggers it — confirmed with a plain PEP 695 `type X[T] = T` alias, not just
  `Annotated`; judged a mypy bug, not a real constraint). For mypy users: `@mut`
  decorator (recommended), per-line `# type: ignore[misc]`, project-wide `misc`
  suppression (not recommended), or a different checker.
- **Implicit inference** (from method body) rejected — contradicts "no defaults, ever."
  **Hand-rolled bound `TypeVar`** works on ty+mypy but needs one declaration per class
  for no benefit over `@mut`. Class decorator to inject it automatically is a dead end
  (runs after class body evaluation; checkers don't execute decorators).
- **Per-field `Mut`/no-`Mut`**: a field not declared `Mut` is locked after construction,
  even for `@mut` methods. Subsumes `typing.Final`. Write requires both field permission
  (declaration-time) and caller permission (`Mut` on receiver, call-site).
- **Construction exemption**: fields writable while the object hasn't escaped the
  constructing code (covers `__init__`, `__post_init__`, `__new__`, classmethod
  constructors — escape, not method name, governs). The escape check is bounded and
  single-object, not general aliasing — but not yet designed.
- **Deep immutability for free**: a type with no `Mut` fields anywhere in its graph is
  unconditionally, transitively immutable — visible from its own declaration, no
  per-level bookkeeping needed.

## Implementation architecture

### Private `ty` backend

The tool ships its own pinned `ty` binary (MIT-licensed, standalone compiled Rust
executable — no Python-level install, no namespace collision). Users never interact with
it directly, and it doesn't conflict with any `ty` the user might have installed
separately. The tool invokes it by absolute path via LSP (`didOpen`/`didChange`,
reading `publishDiagnostics`).

### Intersection types (internal only)

`ty` supports intersection types (`Intersection` from `ty_extensions`). The tool's
private `ty` instance is configured (via `extra-paths` in its `ty.toml`) to resolve
the library's module to an intersection-based definition: `type Mut[T] =
Intersection[T, MutMarker]`. This gives a real, preserved type — unlike `Annotated`
(which `ty` erases completely), intersections survive generic substitution and
inheritance (confirmed: `Container[int].item` → `int & MutMarker`).

Users' own type checkers see none of this. They resolve the library normally and find
the plain default definition (`type Mut[T] = T`), which is transparent — `Mut[int]` is
just `int` to mypy/pyright/anything else, zero configuration needed, zero breakage
possible.

### Hybrid enforcement: `ty` + custom filter

`ty` natively enforces `Mut[T] <: T` — a `Mut[T]` value is accepted where `T` is
expected. But the reverse (plain `T` assigned to a `Mut[T]` position) is rejected,
since a plain value genuinely lacks `MutMarker`. This is correct per intersection
semantics but wrong for this system, where plain values should satisfy `Mut` positions.

**Solution**: suppress `ty` diagnostics whose message contains `not assignable to
element \`MutMarker\`` where the source type carries no marker. Everything else — real
type mismatches, ordinary Python errors — passes through unmodified. Confirmed working
through `ty`'s LSP `publishDiagnostics` (info lines embedded in the message field,
fully parseable) — **for plain assignment and tuple-unpacking only**. For-loop and
`with`-statement pre-declared targets (see below) raise the same `invalid-assignment`
code but their `message` field never contains the `MutMarker` explanation — confirmed
directly via raw LSP `publishDiagnostics` payloads, not just CLI rendering (`ty check
--output-format concise` independently corroborates the same absence). The filter must
also match on the primary message shape (`is not assignable to \`Mut[`) rather than
relying on the `MutMarker` sub-string alone, or these two pre-declaration forms will
leak real-looking errors to users for code the design explicitly says should be silent.

The custom pass still owns: transitivity/reachability, per-field `Mut` locks, and the
construction-escape check — these aren't type-compatibility questions.

## Syntax and ergonomics

### Locals require `Mut` for reassignment

Unannotated local `T` is read-only — reassignment is an error, same as for fields.
`Mut[T]` on an immutable type (e.g. `Mut[int]`) means the *binding* can be reassigned,
since there's nothing else to mutate.

### Constructors and literals satisfy `Mut` positions

`x: Mut[list[int]] = [1, 2, 3]` is allowed — fresh values are provably unaliased at
creation. This is the same construction-time exemption as for fields, applied to
assignment. At `ty`'s level, these produce a false-positive (`T not assignable to
MutMarker`) that the filter already suppresses.

### Pre-declaration for loops, unpacking, and `with`

No post-assignment annotation — `ty` rejects it as a conflicting declaration. Instead,
pre-declare the binding's type, then assign:

```python
i: Mut[int]
for i in range(5): ...       # i is Mut[int] per the pre-declaration

a: Mut[int]
b: int
a, b = pair                  # unpacking into pre-declared bindings

f: Mut[io.StringIO]
with io.StringIO() as f: ... # f is Mut per the pre-declaration
```

All produce the standard false-positive that the filter suppresses; `reveal_type`
confirms the declared `Mut` type is respected in each case (confirmed directly).

Unpacking without pre-declaration produces immutable bindings by default.

For loops specifically: pre-declaring `Mut[T]` is only required if the loop body
reassigns or mutates the target (`i += 1`, `i.append(...)`, etc.) — each iteration's
implicit binding is effectively fresh, the same construction exemption as any other
new value, not a reassignment needing permission. A loop that only reads its target
(`for i in range(5): print(i)`) needs no `Mut` at all (confirmed directly). This
distinction is invisible to `ty` itself — it flags the implicit per-iteration binding
against a `Mut[T]`-declared target the same way regardless of what the body does —
so it's enforced by whether the fixture/code pre-declares `Mut` in the first place,
not by anything `ty` decides.

### Comprehensions are exempt

Comprehension variables are scoped to the comprehension (Python 3, PEP 289) — no
annotation mechanism can reach them from outside, pre or post. Mutation permission for
comprehension iteration variables is derived from the source iterable's element type
by the custom pass via AST inspection, not from a type annotation on the variable
itself.

### Container content mutability is compositional

`Mut[list[User]]` and `Mut[list[Mut[User]]]` are genuinely different permissions:
- `Mut[list[User]]`: can restructure the list (`append`, `pop`, `x[0] = other`) but
  cannot mutate the `User` objects inside it.
- `Mut[list[Mut[User]]]`: can restructure the list *and* mutate its elements.

This matches Rust's `&mut Vec<&T>` vs `&mut Vec<&mut T>` distinction.

### Stdlib and third-party support

The tool provides its own type stubs for stdlib mutating methods (`list.append`,
`dict.update`, `set.add`, etc.), fed to the private `ty` instance via `extra-paths`.
Same mechanism for third-party libraries as needed. This is a real, ongoing maintenance
burden — the stdlib surface is large and evolves across Python versions.

### Target audience

These rules are stricter than most Python developers would tolerate. The target
audience is developers who prefer functional-style programming and want strict static
guarantees of correctness.

## Incremental adoption

**Mypy-style scope-level opt-in**: if a function (or file, or module) has zero `Mut`
annotations, the checker skips it entirely — no mutability violations reported. A scope
with *any* `Mut` annotation is fully checked. This is the ratchet: adding `Mut` to one
function commits you to annotating that function completely, but you never have to start
until you're ready. Adding `Mut` to one function does not require adding it to every
other function that touches the same values.

## Open

- Untyped-code handling: configurable (strict/permissive/ignored), default permissive.
  Details not designed.
- Construction-escape check: needs its own design.
- Full backend integration: architecture decided and empirically validated, not yet
  built.
- Stdlib stubs: scope and initial coverage not yet determined.
