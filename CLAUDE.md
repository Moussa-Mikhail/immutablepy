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
--output-format concise` independently corroborates the same absence) — and augmented
assignment (`total += i`) turns out to have the same gap, confirmed the same way.

Two filters now cover this, by different means. `mut_check._filter.filter_construction_exemption`
treats every `for`/`with` target-binding location as exempt unconditionally (any type,
via AST inspection matching the diagnostic's exact `(line, col)`) — sound because once a
target is declared `Mut[T]`, `ty` already treats it as `Mut[T]` for the rest of the
scope regardless of whether this one diagnostic is shown (confirmed via `reveal_type`),
so suppressing it loosens nothing real. `mut_check._immutable.filter_immutable_type_exemption`
separately falls back to the primary message shape (`Object of type \`X\` is not
assignable to \`Mut[`) when the info line is missing, covering augmented assignment
(`total += i`) for immutable `X`. Augmented assignment on a *mutable* `X` (e.g. a
custom `__iadd__` returning a fresh, unmarked value) remains an open gap — no fixture
exercises it yet.

The custom pass still owns: transitivity/reachability, per-field `Mut` locks, and the
construction-escape check — these aren't type-compatibility questions. Its first piece
now exists (`mut_check._reassignment`): plain-local/parameter reassignment without
`Mut` — see "Locals require `Mut` for reassignment" below.

## Syntax and ergonomics

### Locals require `Mut` for reassignment

Unannotated local `T` is read-only — reassignment is an error, same as for fields.
`Mut[T]` on an immutable type (e.g. `Mut[int]`) means the *binding* can be reassigned,
since there's nothing else to mutate.

**Enforced by `mut_check._reassignment`** (`ty` has no notion of this at all — confirmed
directly, it reports nothing for `for i in range(5): i += 1` with no `Mut` anywhere).
Applies to locals and parameters, `ast.Name` targets only (attribute writes are a
separate, not-yet-designed rule — per-field locks/construction escape). A local's first
real assignment is always free, establishing it as non-`Mut` by default unless already
declared otherwise; every assignment after that (plain or augmented — augmented always
presupposes an existing value) needs `Mut`. Parameters have no free first assignment,
since the call itself already bound them. `for`/`with`/unpacking target bindings
establish/preserve status but are never themselves a violation, matching the exemption
`mut_check._filter` already gives the corresponding `ty` diagnostics — only a
*subsequent* reassignment inside the body is checked. A bare `AnnAssign` (`x: T`, no
value) sets permission only, not boundness — conflating the two was a real bug caught
while building this (`b: list[int]` followed by unpacking into `b` looked like a second
assignment). Scoping (function/lambda/class/comprehension) matches real Python rules;
`global`/`nonlocal` aren't modeled, so an unmodeled name is never flagged (false
negatives preferred over false positives for a first pass).

### Immutable types always satisfy `Mut[T]`, aliased or not

A value of an immutable type (`int`, `str`, `bytes`, `float`, `bool`, `complex`,
`frozenset`, `tuple`, ...) is special-cased to always be assignable/passable to a
`Mut[T]` position, whether it's freshly constructed or an aliased reference from
anywhere — there's no mutation hazard to protect against, since nothing can mutate an
immutable value through any reference. This supersedes treating an aliased plain `int`
passed where `Mut[int]` is expected as a rejection; that's no longer correct.

`tuple` qualifies regardless of its element types — `tuple[list[int], int]` is exempt
the same as `tuple[int, str]`, since a tuple itself has no mutating operations at all
(no item assignment, no `append`/`pop`); aliasing the tuple binding can never expose a
way to restructure it. Mutating an element reached through the tuple (e.g. the `list`
inside `tuple[list[int], int]`) is governed by that element's own `Mut` annotation
(`tuple[Mut[list[int]], int]`), independent of whether the tuple binding itself needed
`Mut` — the same compositional split as "Container content mutability is compositional"
below, just starting from a container that's unconditionally immutable itself.

**Generalizes to read-only abstract types.** The actual criterion was never "is this
type on a fixed concrete list" — it's "does this type's own interface expose any
mutating operation, regardless of what it holds." That test also passes for structural
read-only types with no mutating members in their own definition: `Sequence[T]`,
`Mapping[K, V]`, `Collection[T]`, `Iterable[T]`, `Iterator[T]`, `Container[T]`, `Sized`,
`Hashable`, `Reversible`, the `*View` types, ... — `Mut[Sequence[T]]` grants nothing a
plain `Sequence[T]` reference couldn't already do, same as `tuple`. `MutableSequence`/
`MutableMapping`/`MutableSet` stay excluded, same as `list`/`dict`/`set` — that's the
whole reason those `Mutable*` names exist. Enforcement here is purely static, so even
if the runtime object behind a `Sequence[int]`-typed reference happens to be a mutable
`list`, the reference's own type structurally forbids mutating through it — the same
structural-typing argument that already justifies everything else in this design.
Hand-maintained allowlist, same as the concrete types above, not derived from
structure.

**Not the same thing as "immutable types are `Mut` by default."** The local-reassignment
rule above is untouched: `x: int` still can't be reassigned without `Mut[int]` on its
declaration. What changes is only the *other direction* — once something requires
`Mut[T]` for an immutable `T`, any value of that type satisfies it, unconditionally.

This also means the typeshed/`__builtins__.pyi` stubbing route (see "Stdlib and
third-party support") is only needed for genuinely **mutable** stdlib types (`list`,
`dict`, `set`, `bytearray`, ...), where a returned value's aliasing actually matters.
Immutable-type dunders like `int.__add__` don't need `Mut`-aware return-type stubs at
all — the special case makes that unnecessary regardless of what the method returns.

### Constructors and literals satisfy `Mut` positions

An object created in the current scope can be assigned/passed/returned as `Mut` —
provably unaliased at that point, nothing else could hold a reference yet. This is the
same construction-time exemption as for fields, generalized: `x: Mut[list[int]] = [1,
2, 3]` (assignment), `def f() -> Mut[Box]: return Box()` (return value),
`f(Box())` where `f`'s parameter is `Mut[Box]` (call argument) — `ty` always points its
false-positive diagnostic at the fresh expression's own position regardless of which of
these three it is, so `mut_check._filter.filter_construction_exemption` matches purely
on position, with no need to special-case `AnnAssign`/`Return`/`Call` separately.
Literal displays and comprehensions/generator expressions always count as fresh.
Calls are narrower — only **class-instantiation calls**, not arbitrary function calls:
instantiating a class has a *language-level* freshness guarantee (`__new__` always
allocates, whatever `__init__` does with it) that an arbitrary function's return value
doesn't have. An earlier version treated any bare-name call as fresh, which meant
inferring freshness for `get_values()` (an ordinary function) from its *implementation*
(happened to construct fresh lists) rather than its *declared return type* (plain, no
`Mut` anywhere) — exactly the "no implicit inference from bodies" mistake this design
already rejects elsewhere (see "Methods and per-field mutability" above), just not
caught here until the fixture built on that premise was checked against it. So a
bare-name call only counts if the name is a locally-`class`-defined name or a built-in
mutable-container constructor (`list`, `dict`, `set`, `bytearray`) — immutable built-in
constructors aren't needed here since `_immutable` already exempts those by type name
regardless of origin. **Except** method calls (`obj.method(...)`): the call's own AST
position coincides with the *receiver* `obj`'s, not with anything the call returns, so
treating every call as fresh wrongly exempted `c.increment()` on a plain, genuinely
aliased receiver `c` (confirmed as a real overreach bug too). Also confirmed: matching
on any `Mut[` mention anywhere in a diagnostic's text is too broad, since a Protocol
structural mismatch (see "Protocols" above) can mention `Mut[` three levels deep inside
a `└──` tree explaining an unrelated per-field type mismatch — the filter only matches
non-nested lines.

This can't distinguish a constructor that returns fresh state from one that returns a
cached/shared object — same structural-typing tradeoff the rest of this design already
makes. Not covered: a `Name` referring to a value obtained earlier (even from a fresh
call) — only the call/literal/comprehension's own position is exempt, not every later
reference to whatever it produced; or calls to imported/external classes (only
locally-`class`-defined names are recognized, a static AST check, not a name lookup).

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

**Scope**: only genuinely mutable stdlib types (`list`, `dict`, `set`, `bytearray`,
...) need any of this — see "Immutable types always satisfy `Mut[T]`" above.
`int.__add__` was the method used to investigate the mechanism below, but per that
special case it turns out to need no stub at all, regardless of what it returns.

**The dunder name `__builtins__.pyi` does work**, on `ty` 0.0.79 (currently
installed) — matching pyright/pyrefly's convention, per
[PR #22021](https://github.com/astral-sh/ruff/pull/22021), it layers custom
definitions on top of vendored typeshed instead of replacing it. Confirmed with
non-literal operands (`a: int, b: int; a + b`) — literal operands like `1 + 2` don't
work as a test, since `ty` constant-folds them to `Literal[3]` without ever
consulting `int.__add__`'s stub, masking whether an override took effect either way.
Works through our own intersection mechanism too: `int.__add__` stubbed to return
`Mut[int]` makes `x: Mut[int] = a + b` type-check clean. It's discovered via
`extra-paths`, not just the literal project root — confirmed placing it in
`stubs/internal/` (already on our private `ty`'s `extra-paths`) is picked up
correctly. A bare attribute-annotation patch attempt (`int.__add__: Callable[[int,
int], Mut[int]]` at module level, without a full `class int:` block) does *not*
work — `ty` silently ignores it as a patch target (confirmed via
`reveal_type(int.__add__)` still showing the real signature); only actual
`class`/`def` redefinitions are recognized.

**The real catch: whole-class replacement, not per-method patching.** Redeclaring
`class int:` with only `__add__` silently drops every other member — `bit_length`,
`__sub__`, `__mul__`, etc. all became `unsupported-operator`/`unresolved-attribute`
errors in testing. Brand-new top-level names and untouched classes are unaffected, so
it's additive at the *module* level but replacing at the *class* level. Using this for
a mutable type like `list`/`dict`/`set` therefore means copying that class's *entire*
member set from real typeshed once (not the whole stdlib — just the specific classes
touched), modifying only the signatures that need `Mut`-awareness (e.g. `list.append`
taking a `Mut`-aware element type when the list itself is `Mut[list[Mut[User]]]`).
Not yet built. The AST-filter alternative (recognizing `list.append`-style calls as
construction-exemption cases in `mut_check._filter`) remains a viable fallback that
avoids tracking typeshed at all — worth weighing against this once someone actually
implements either.

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
