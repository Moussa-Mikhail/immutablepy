# Decision Log — Rust-Inspired Mutability System for Python

Rationale, rejected alternatives, and confirmation/testing trails behind the rules in
`../CLAUDE.md`. Read this when you need to know *why* something is the way it is, or
before reopening a question that looks settled here.

## Core model

Lattice: `Mut[T] <: T`. Pony's 6-tier system was reviewed and rejected — its extra
tiers need whole-program alias analysis, infeasible in Python. Finer granularity within
`Mut` (insert/remove/overwrite sub-permissions) also declined.

## Rejected: type-broadening lint

Suggesting `list[T]` → `Sequence[T]` when a parameter is never mutated: rejected. If
the function later needs mutation, walking back costs two edits versus one — the lint
would be making a speculative bet on the user's behalf.

## No type defaults to `Mut`, ever

`list`/`dict`/`set`: rejected (habit, not signal) -- stays rejected, see "Concrete
container types excluded" below.

`MutableSequence`/`MutableMapping`/`MutableSet`: originally also rejected on the same
counterexample -- `s = o.mutset` where `o` isn't `Mut` -- reasoning that the type
carries no memory of origin, so defaulting by type alone leaks permission through the
transitivity boundary. **Superseded** -- see "Fields inherit mutability from the owner"
below (which also supersedes the narrower `Mutable*`-only default proposed in "Open
design: field-permission default for `Mutable*` fields"): the counterexample only holds
if the field's own declared type is the sole gate. With the gate moved to the access
path, the leak this was rejecting doesn't reoccur, because it shifts from "trust the
field's static type" to "trust the path used to reach it" -- the same shift
transitivity already makes for every other reachability question in this system.
`Mutable*` ABCs remain the recommended spelling over concrete types either way.

## Transitivity of `Mut` — kept, no override

Without transitivity, a permission check at a function boundary is bypassable via any
attribute chain — the check becomes theater. Cost accepted: permission virality (same
class as Rust's `&mut` propagation) and no field-scoped grants. A per-field override
(letting a class cap transitivity) was rejected — Rust's answer to this is
module-privacy, which Python already has. Field locks were a form of exactly this cap;
see "Fields inherit mutability from the owner" for dropping them. That section also adds
the one deliberate exception in the other direction (an outer `Mut` on a field), which
*uncaps* transitivity for state the class author opts in.

## Protocols

Structural conformance under `Annotated`-based erasure is blind to `Mut` tags — a class
can declare a field locked while a protocol it satisfies claims `Mut`, with nothing
catching the mismatch (confirmed directly). **Resolved by the intersection-type
approach**: `ty`'s own protocol-conformance checking catches this natively once
protocol members use real intersection-typed `Mut`. Usage-driven (fires at real call
sites), not exhaustive N×M. Remaining gap: unanalyzed third-party code — the general
untyped-code limitation, not Protocol-specific.

**Update (2026-10-06):** with inherited mutability (see "Fields inherit mutability from
the owner") no field is locked, so the scenario above -- a class locking a field a
protocol claims is `Mut` -- can no longer arise. (A protocol member declared `Mut[...]`
now has a meaning of its own, an always-mutable attribute -- see "Escape hatch" -- and
a class whose field is plain doesn't satisfy it; `ty`'s native check catches that, but
it isn't the removed fixture's scenario.) Whether a protocol attribute is
*settable* is Python's own rule, and every checker already enforces it without `Mut`:
confirmed that `ty`, mypy and pyright all reject both a read-only `@property` and a
`Final` attribute against a protocol attribute `value: int` (mypy: "expected settable
variable, got read-only attribute"). `mut_check_protocol_conformance_bad.py` and its
test (`test_protocol_conformance_catches_mut_mismatch`) pinned `ty`'s `Mut`-tag mismatch,
no longer a real scenario, and were removed. That test was also the only one exercising
`mut_check._filter`'s "ignore `Mut[` mentions nested under a `└──` tree" restriction;
`test_nested_mismatch_is_not_suppressed_as_a_fresh_construction` now pins that instead,
using a protocol *method* returning `Mut[...]` (a real mismatch with the same nested
shape, no field mutability involved), with a matching control. Confirmed it fails when
the restriction is removed.

Note: Python's `Protocol` works with zero textual relationship between class and
protocol — no import, no inheritance, no reference at all (confirmed against `typing`
docs). Relevant because any custom verification would need real pairwise structural
comparison, not reference-following — but since `ty` handles this natively now, that
cost is avoided entirely.

## Methods and per-field mutability

- **`Mut[Self]`** is the default way to mark mutating methods. mypy hard-errors on this
  (bug report filed for `Annotated[Self, ...]` specifically — not for the plain PEP
  695 `type X[T] = T` alias case, e.g. `Mut[Self]` itself; that one's confirmed as
  the same underlying issue but not independently reported. Bare `self: Self` is
  accepted, wrapping `Self` in *any* generic alias triggers it either way — judged a
  mypy bug, not a real constraint). For mypy users: `@mut` decorator (recommended),
  per-line `# type: ignore[misc]`, project-wide `misc` suppression (not
  recommended), or a different checker.
- **Implicit inference** (from method body) rejected — contradicts "no defaults, ever."
  **Hand-rolled bound `TypeVar`** works on ty+mypy but needs one declaration per class
  for no benefit over `@mut`. Class decorator to inject it automatically is a dead end
  (runs after class body evaluation; checkers don't execute decorators).
- **Construction writes**: constructors (`__init__`, `__post_init__`, `__new__`,
  classmethod constructors) need to write the new object's fields. Originally framed as
  an escape check ("writable while the object hasn't escaped") because fields were
  locked afterward; with inherited mutability nothing is locked afterward, so the escape
  check isn't needed -- only a way to grant constructors write permission on `self`
  (likely an implicit `Mut`). Not yet designed.

## Fields inherit mutability from the owner — no field locks

**Status (decided 2026-10-06, updated 2026-10-06):** field *reads* (inheritance) and the
`Mut`-field escape hatch are implemented and tested. Not built: attribute *write*
checks and constructor writes (see "Follow-ups"). The old protocol fixture/test and the
stale source comments are removed (the `_filter` nested-tree rule that fixture pinned
has a replacement test).

**Decision.** Fields have no mutability of their own. Through a `Mut` owner (including
`self` in a `Mut[Self]`/`@mut` method) a field is writable/mutable; through a read-only
owner it is read-only. A plain field annotation carries no mutability of its own; an
outer `Mut` on a field annotation is the escape hatch below. `Mut` nested in type
arguments (`list[Mut[User]]`) stays explicit, exactly as in "Container content
mutability is compositional". This replaces the earlier rule that a field not declared
`Mut` is locked after construction, even for `@mut` methods.

**Why drop locks.**

- The only thing a lock added was stopping a class's *own* methods from changing a
  field. That's author-controlled code, and Python already has enforced spellings for it:
  `typing.Final` (no rebinding, including from the class's own methods), a read-only
  `@property`, and immutable/read-only field types (`tuple`, `frozenset`, `Sequence`,
  `Mapping`) for contents. The "Open design" section below already endorsed the last
  one as how to say "permanently locked".
- A lock is a per-field cap on transitivity, which "Transitivity of `Mut`" already
  rejected, on the argument that Rust's answer is module privacy. Keeping locks was the
  inconsistent half.
- Rust doesn't have them either: a `&mut self` method can assign any field of the type;
  the closest tool is privacy, not a per-field immutability marker.
- Locks dragged three undesigned pieces behind them -- the lock check itself, the
  construction-escape check, and the `Mutable*` field-permission default -- each only
  needed because a field could carry its own permission.

**What's lost.** A lock that survives a fully-`Mut` owner on a field of *mutable* type
without changing the field's declared type. And the derivation "a type with no `Mut`
fields is deeply immutable" -- never built; "Immutable types always satisfy `Mut[T]`"
stays a hand-maintained allowlist either way.

**Field access typing (implemented 2026-10-06, read side only).** `type_of(o.field)` inherits
`o`'s `Mut`-ness for the *outer* level: `Mut[declared]` through a `Mut` owner, plain
`declared` through a read-only one. Nested `Mut` is untouched. This is the same
attenuation mechanism as piece (1) of the superseded "Open design" section, and it
closes the same leak (`s = o.mutset` where `o` isn't `Mut`): through a read-only `o`,
`o.mutset` is read-only, so there's nothing to leak. It no longer needs piece (2), the
`Mutable*`-only field-permission default -- every field type behaves the same way.

*How:* no custom pass, no `ty` change. `MutMarker` in `stubs/internal/immutablepy`
gets `def __getattr__(self, name: str) -> MutMarker | MethodType | FunctionType`.
`ty` resolves attributes on an intersection through every element, so on
`T & MutMarker` an attribute is `declared & MutMarker`; on plain `T` it's untouched.
Tested by `test_mut_check_field_inheritance.py`; confirmed each test fails under the
stub variants it guards. Findings from getting there:

- The union is load-bearing. A bound method and a `MutMarker` instance are disjoint,
  so a bare `-> MutMarker` collapses every method to `Never`, silently disabling call
  checking on `Mut` receivers (the existing container test caught this). `MethodType`
  alone keeps instance methods but static/class methods still go to `Never`;
  `FunctionType` alone breaks instance methods; both are needed. Both are `@final`, so
  they are disjoint from data attributes and drop out. `Callable[..., object]` fails: it
  leaves a `& ((...) -> object)` residue on every attribute.
- A callable-typed field (`cb: Callable[[int], int]`) no longer collapses to `Never`,
  but its type through a `Mut` owner is a three-branch union. Left as is: rare.
- Typos: `__getattr__` makes every name resolve on a `Mut` owner, so `u.nmae` raises no
  `unresolved-attribute` under `immut check`. Accepted -- the user's own checker sees
  the plain transparent `Mut[T] = T` and still reports it.
- Writes are only partly covered: `ty` checks `o.field = v` against the *declared* type.
  For a plain-annotated field, neither a plain owner nor a plain value written through
  a `Mut` owner is reported. For a `Mut`-annotated field the declared type carries the
  marker, so a plain reference is rejected (see "Escape hatch").

**Escape hatch: an outer `Mut` on a field annotation (decided 2026-10-06).** A field
annotated `Mut[...]` is mutable through *any* owner, even a plain one. This reframes what
had been "redundant but allowed": with field access typing it isn't redundant (the marker
rides in on the declared type, so it survives a read-only owner) and it isn't harmless,
so it is made the point instead of being diagnosed or stripped. It is interior
mutability, as with Rust's `Cell`/`RefCell`/`Mutex`: state a logically read-only method
updates -- a memo, a counter, a log buffer -- without making the method `Mut[Self]` and
so infecting every caller.

*Tradeoff:* this is the one deliberate hole in transitivity. A function taking a plain
`T` can no longer guarantee it can't mutate that class's marked fields. "Transitivity of
`Mut`" rejected field-level overrides that *cap* transitivity; this *uncaps* it, only
where the class author opts in on the field's own annotation, so it is greppable (`Mut[`
on a field) and confined to declared interior state. Transitivity stays the rule; this
is its single documented exception.

*Behavior* (pinned by `test_mut_check_field_inheritance.py`): a plain-`self` method or a
plain parameter can mutate such a field; initializing it with a fresh value is accepted
in both forms (`self.x = {}` and `self.x: Mut[...] = []`); storing a plain reference in
it is rejected, since that would hand mutation access to something its other holders
can't mutate. Rebinding through a plain owner follows the same rule (fresh value fine,
plain reference rejected). Getting there needed two fixes to the construction exemption
in `mut_check._filter`: `ty` words the attribute form "assignable to attribute `x` of
type `Mut[...]`", which the old message pattern missed, and it points at the whole
attribute target rather than the value, so the exemption is also keyed on the target of
an assignment whose value is fresh (assignment and annotated assignment only -- a fresh
right-hand side of `+=` says nothing about whether the result is fresh).

*Spelling:* it reuses `Mut`, so on a field it means "always mutable", unlike on a
parameter, where it means "permission to mutate". Revisit if that reads confusingly.

**Follow-ups (not done).**

- Constructor writes: how a constructor gets write permission on its own object
  (likely an implicit `Mut` on `self`). Replaces the construction-escape check.
- Attribute writes (`o.field = v`, also augmented): "requires `Mut` on the owner" is
  unchecked today (see above). Candidate: extend `_reassignment`'s per-scope permission
  map to `Attribute` targets rooted at a name; `self` is `Mut` when the method has
  `self: Mut[Self]`/`@mut`, and in constructors. It must exempt fields annotated with an
  outer `Mut` (always mutable), which needs the field's annotation, not just the owner's
  name.
- Subscript writes through a field (`self.memo[key] = 1`) still hit the open `ty`
  subscript-assignment bug.

## Open design: field-permission default for `Mutable*` fields, gated by read attenuation

**Superseded (2026-10-06)** by "Fields inherit mutability from the owner" above, which
makes every field inherit its owner's `Mut`-ness and so needs no field-permission
default at all. Piece (1) below survives as the "Field access typing" proposal there;
piece (2) is dropped. Kept as the trail.

Not yet designed or built -- both pieces below have to land together, in this order of
dependency, or the older leak this reopens comes right back. Confirmation trail: none
yet, this is a design proposal, not a built/tested behavior.

**The two pieces, and why they're coupled:**

1. **Read-side attenuation** (the actually new mechanism; nothing today computes this):
   `type_of(o.field)` is not just `field`'s declared type -- it's attenuated by `o`'s
   own `Mut`-ness. Concretely: `type_of(o.field) = declared_type if o is Mut[...] else
   strip_outer_mut(declared_type)`. This is the write-side rule ("Write requires both
   field permission and caller permission" in CLAUDE.md's "Methods and per-field
   mutability") applied symmetrically to reads -- the caller-permission half of that
   check is already unavoidable machinery for field *writes*; this reuses it for field
   *reads* instead of leaving reads ungated. Only the *outer* `Mut` is attenuated --
   nested type-parameter `Mut`s (the "container mutability is compositional" case,
   `Mut[list[Mut[User]]]` vs `Mut[list[User]]`) are untouched by this and stay exactly
   as explicit as they are today. Without this piece, defaulting field-permission (2)
   is unconditionally unsound -- it's the same leak `s = o.mutset` was originally
   rejected for, just relocated from "the field's static type is trusted alone" to
   "the field's static type is trusted alone, and now the default makes that type say
   yes more often." Scope note: presumably applies symmetrically to a method returning
   `self.field` un-`Mut`-wrapped, attenuated by the method's own receiver -- same
   reasoning, not yet confirmed against a fixture.

2. **Field-permission default, `Mutable*` ABCs only.** With (1) in place, a field typed
   `MutableSequence[X]`/`MutableMapping[K, V]`/`MutableSet[X]` (no explicit outer `Mut`)
   defaults to Mut-capable -- reachable through it is exactly what (1) already gates by
   the access path, so the field's own declared type no longer needs to *also* carry
   that bit. Rationale for restricting this to the ABCs, not extending it to concrete
   `list`/`dict`/`set`/`bytearray` field types: choosing `MutableSequence` over
   `Sequence` (its exact non-mutating sibling) is a binary, already-made choice with no
   other reason to prefer one name over the other -- real signal, not "habit, not
   signal" the way bare `list` is (no meaningfully different concrete type says "this
   one's read-only"). A field that's genuinely meant to be permanently locked, even
   through a fully-`Mut` receiver, spells that by choosing the non-mutating protocol
   (`Sequence`) in the first place -- the field-permission axis from CLAUDE.md's
   per-field rule doesn't disappear, it's just now spelled by the type-family choice
   itself instead of by a separate `Mut` wrapper on top of it, for this one family of
   types. Concrete container field types are explicitly excluded from this default and
   keep requiring an explicit outer `Mut` wrapper, same as today.

## Implementation architecture

### Private `ty` backend

The tool ships its own pinned `ty` binary (MIT-licensed, standalone compiled Rust
executable — no Python-level install, no namespace collision). Users never interact with
it directly, and it doesn't conflict with any `ty` the user might have installed
separately.

**Invoked as a CLI subprocess (`ty check`), not via LSP**, despite `Mut`-marker
filtering having been prototyped and confirmed against raw LSP `publishDiagnostics`
payloads first (see "Hybrid enforcement" below). Both pathways were evaluated end to
end — `ty` CLI output + text parsing, vs. `ty` LSP (`didOpen`/`didChange` +
`publishDiagnostics`) + reimplementing formatting — and LSP was rejected because its
diagnostic payload is unformatted plain text with no equivalent to the CLI's
human-oriented rendering (colored output, gutter/pointer layout, `└──` diagnostic
trees); using it would have meant reimplementing `ty`'s own formatting code, which was
rejected as unnecessary work for no functional gain. `mut_check._ty.run` instead shells
out to `ty check --color=always` and parses its rendered stdout directly (regex over
`error[code]:` headers and `--> file:line:col` locations in `mut_check._ty._parse`), so
`immut check`'s output is `ty check`'s output, verbatim, with only bad diagnostics
filtered out — no reformatting step of its own to keep in sync with `ty`'s.

This choice is scoped to today's CLI tool, which wants `ty`'s own human-rendered
output verbatim. A possible future IDE plugin (far off, not yet designed) wouldn't
face the same tradeoff — an editor renders diagnostics itself from structured LSP
fields (range, severity, message), so it would consume `publishDiagnostics` directly
with no formatting to reimplement; it just wouldn't reuse this CLI-subprocess code
path.

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
type mismatches, ordinary Python errors — passes through unmodified. This was
prototyped and confirmed against `ty`'s raw LSP `publishDiagnostics` payloads (info
lines embedded in the message field, fully parseable) before the CLI-subprocess
approach was settled on (see "Private `ty` backend" above) — the filtering logic
itself is unaffected by which transport it came from, since both expose the same
message text. Confirmed working **for plain assignment and tuple-unpacking only**.
For-loop and `with`-statement pre-declared targets raise the same `invalid-assignment`
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

The custom pass still owns: transitivity/reachability, attribute writes through a `Mut`
owner, and constructor writes — these aren't type-compatibility questions. Its first piece
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
separate, not-yet-designed rule — a write requires `Mut` on the owner). A local's first
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

**Known limitation: `*args`/`**kwargs` can never be reassigned.** `_param_scope` hardcodes
both as non-`Mut`. There's no parameter-level spelling that could change that: an
annotation on a vararg describes each *element*, not the binding (`*args: Mut[list[int]]`
is `tuple[Mut[list[int]], ...]` per `ty`, with `args` itself still read-only). The only
opt-in is redeclaring the name in the body (`args: Mut[tuple[int, ...]] = args`) --
`mut_check` and `ty` both accept that, but mypy rejects it (`no-redef`) and pyright
rejects it (`reportRedeclaration`), which breaks the "other checkers see plain code"
goal. Not weighed when first written (it hadn't come up), and rare enough in practice
that it's accepted as-is; revisit only if someone actually needs to reassign a vararg.
Pinned by `test_varargs_try_body_and_post_lambda_reassignment_are_each_flagged`.

### Immutable types always satisfy `Mut[T]`

A value of an immutable type (`int`, `str`, `bytes`, `float`, `bool`, `complex`,
`frozenset`, `tuple`, ...) is special-cased to always be assignable/passable to a
`Mut[T]` position, regardless of where it came from — a fresh literal or a `Name`
pointing to an existing binding, it makes no difference. This isn't about aliasing:
`Mut` tracks per-binding permission, not object uniqueness or exclusivity (it's not
Rust's `&mut` — see "Core model"), and says nothing about whether some *other* binding
also has `Mut` on the same object. The actual reason: for a type with zero mutating
operations, `Mut[T]` and `T` grant exactly the same set of possible operations — there
is no permission gap for `Mut[T]` to protect in the first place. This supersedes
treating a plain `int` passed where `Mut[int]` is expected as a rejection; that's no
longer correct.

`tuple` qualifies regardless of its element types — `tuple[list[int], int]` is exempt
the same as `tuple[int, str]`, since a tuple itself has no mutating operations at all
(no item assignment, no `append`/`pop`); nothing about the tuple binding itself can
ever expose a way to restructure it, regardless of how many bindings point to it.
Mutating an element reached through the tuple (e.g. the `list` inside
`tuple[list[int], int]`) is governed by that element's own `Mut` annotation
(`tuple[Mut[list[int]], int]`), independent of whether the tuple binding itself needed
`Mut` — the same compositional split as "Container content mutability is compositional"
in CLAUDE.md, just starting from a container that's unconditionally immutable itself.

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
rule is untouched: `x: int` still can't be reassigned without `Mut[int]` on its
declaration. What changes is only the *other direction* — once something requires
`Mut[T]` for an immutable `T`, any value of that type satisfies it, unconditionally.

This also means the typeshed/`__builtins__.pyi` stubbing route (see "Stdlib and
third-party support") is only needed for genuinely **mutable** stdlib types (`list`,
`dict`, `set`, `bytearray`, ...), where `Mut[T]` and `T` genuinely differ in what they
permit. Immutable-type dunders like `int.__add__` don't need `Mut`-aware return-type
stubs at all — the special case makes that unnecessary regardless of what the method
returns.

### Constructors and literals satisfy `Mut` positions

An object created in the current scope can be assigned/passed/returned as `Mut`. This
is not an aliasing argument — `Mut` is a per-binding permission that flows through
ordinary type-checking, not a uniqueness/exclusivity guarantee (see "Core model"; this
isn't Rust's `&mut`), and it says nothing about whether some *other* binding also has
`Mut` on the same object. The actual question is whether this expression's type has
already been committed by an earlier declaration, or whether this is its first
appearance. A `Name` reference already has a type fixed by wherever it was declared —
using it where `Mut[T]` is required is an ordinary type mismatch if that declared type
isn't `Mut[T]`. A literal, comprehension, or language-guaranteed-fresh construction
call has no such prior commitment — it's being typed for the first time, right at this
exact use site, free to satisfy whatever the context needs, the same way `x: float = 5`
works even though `5` is literally an `int`. This is the same construction-time
exemption as for fields, generalized: `x: Mut[list[int]] = [1, 2, 3]` (assignment),
`def f() -> Mut[Box]: return Box()` (return value), `f(Box())` where `f`'s parameter is
`Mut[Box]` (call argument) — `ty` always points its false-positive diagnostic at the
expression's own position regardless of which of these three it is, so
`mut_check._filter.filter_construction_exemption` matches purely on position, with no
need to special-case `AnnAssign`/`Return`/`Call` separately.

Literal displays and comprehensions/generator expressions always count as having no
prior commitment. Calls are narrower — only **class-instantiation calls**, not
arbitrary function calls: instantiating a class has a *language-level* freshness
guarantee (`__new__` always allocates, whatever `__init__` does with it); an arbitrary
function's return value has no such guarantee — its type is whatever its *signature*
declares, a real prior commitment regardless of what the body does internally. An
earlier version treated any bare-name call as having no prior commitment, which meant
inferring that for `get_values()` (an ordinary function) from its *implementation*
(happened to construct fresh lists) rather than its *declared return type* (plain, no
`Mut` anywhere) — exactly the "no implicit inference from bodies" mistake this design
already rejects elsewhere (see "Methods and per-field mutability"), just not caught
here until the fixture built on that premise was checked against it. So a bare-name
call only counts if the name is a locally-`class`-defined name or a built-in mutable-
container constructor (`list`, `dict`, `set`, `bytearray`) — immutable built-in
constructors aren't needed here since `_immutable` already exempts those by type name
regardless of origin. **Except** method calls (`obj.method(...)`): the call's own AST
position coincides with the *receiver* `obj`'s, not with anything the call returns, so
treating every call as fresh wrongly exempted `c.increment()` on a plain receiver `c`
— not because `c` is "aliased," but because `c`'s type was already fixed as plain
`Counter` by its own declaration (e.g. a function parameter), the same reason a `Name`
reference is never exempt (confirmed as a real overreach bug too). Also confirmed:
matching on any `Mut[` mention anywhere in a diagnostic's text is too broad, since a
Protocol structural mismatch (see "Protocols") can mention `Mut[` three levels deep
inside a `└──` tree explaining an unrelated per-field type mismatch — the filter only
matches non-nested lines.

This can't distinguish a constructor that returns fresh state from one that returns a
cached/shared object — same structural-typing tradeoff the rest of this design already
makes. Not covered: a `Name` referring to a value obtained earlier (even from a
class-instantiation call) — only the call/literal/comprehension's own position has no
prior commitment, not every later reference to whatever it produced; or calls to
imported/external classes (only locally-`class`-defined names are recognized, a static
AST check, not a name lookup).

### Pre-declaration for loops, unpacking, and `with` — confirmation trail

All three forms (see CLAUDE.md for the syntax) produce the standard false-positive that
the filter suppresses; `reveal_type` confirms the declared `Mut` type is respected in
each case (confirmed directly).

For loops specifically: pre-declaring `Mut[T]` is only required if the loop body
reassigns or mutates the target (`i += 1`, `i.append(...)`, etc.) — each iteration's
implicit binding is effectively fresh, the same construction exemption as any other
new value, not a reassignment needing permission. This distinction is invisible to
`ty` itself — it flags the implicit per-iteration binding against a `Mut[T]`-declared
target the same way regardless of what the body does — so it's enforced by whether the
fixture/code pre-declares `Mut` in the first place, not by anything `ty` decides.

### Comprehensions are exempt

Comprehension variables are scoped to the comprehension (Python 3, PEP 289) — no
annotation mechanism can reach them from outside, pre or post.

## Stdlib and third-party support

**Scope**: only genuinely mutable stdlib types (`list`, `dict`, `set`, `bytearray`,
...) need any of this — see "Immutable types always satisfy `Mut[T]`" above.
`int.__add__` was the method used to investigate the mechanism below, but per that
special case it turns out to need no stub at all, regardless of what it returns.

**Superseded by a vendored `stubs/typeshed` fork.** The `__builtins__.pyi`-override
approach investigated below turned out not to actually work for the real goal, so the
project now ships a full typeshed fork at `stubs/typeshed` instead — CLAUDE.md's
"Implementation architecture" describes the current state. The investigation trail
below (how `__builtins__.pyi` overrides behave, and the whole-class-replacement
constraint) stays, since it's what led to vendoring a full fork rather than patching
just the touched classes in place.

**The dunder name `__builtins__.pyi` only appeared to work, on `ty` 0.0.79 (then
installed)** — matching pyright/pyrefly's convention, per
[PR #22021](https://github.com/astral-sh/ruff/pull/22021), it layers custom
definitions on top of vendored typeshed instead of replacing it. Confirmed with
non-literal operands (`a: int, b: int; a + b`) — literal operands like `1 + 2` don't
work as a test, since `ty` constant-folds them to `Literal[3]` without ever
consulting `int.__add__`'s stub, masking whether an override took effect either way.
Appeared to work through our own intersection mechanism too: `int.__add__` stubbed to
return `Mut[int]` made `x: Mut[int] = a + b` type-check clean, in an isolated file that
only referenced `int.__add__` directly. It's discovered via `extra-paths`, not just the
literal project root — confirmed placing it in `../stubs/internal` (already on our
private `ty`'s `extra-paths`) is picked up correctly. A bare attribute-annotation patch
attempt (`int.__add__: Callable[[int, int], Mut[int]]` at module level, without a full
`class int:` block) does *not* work — `ty` silently ignores it as a patch target
(confirmed via `reveal_type(int.__add__)` still showing the real signature); only
actual `class`/`def` redefinitions are recognized.

**But it doesn't actually override the stdlib's own view of the type.** The override
only defines a *new*, separate `__builtins__.list` (or `int`, etc.) symbol that the
project's own files can reference — it doesn't replace what the rest of vendored
typeshed resolves `list`/`int` to internally. Any stdlib module's stub (or any other
file not importing our override directly) still resolves to the *original*
`builtins.list`, unaffected. That makes it useless for the actual goal: making
`list`/`dict`/`set` uniformly `Mut`-aware everywhere they're referenced, including from
inside other stdlib stubs that use them (e.g. `collections.abc` stubs referencing
`list`). This is the real reason the project moved to replacing the whole `typeshed`
root (`ty.toml`'s `typeshed` setting) instead of layering overrides on top of it — only
a full replacement guarantees every reference, including the stdlib's own
cross-references, resolves to the patched definition.

**A second catch, on top of the one above: the new shadow `int` only has what you
declared on it.** Redeclaring `class int:` with only `__add__` in `__builtins__.pyi`
doesn't touch the real `int` class at all (per the correction above) — it creates a
distinct, separate `int` symbol, and *that* symbol only has `__add__`; any other
member access on it (`bit_length`, `__sub__`, `__mul__`, ...) became
`unsupported-operator`/`unresolved-attribute` errors in testing, because the shadow
type genuinely lacks them, not because anything was "dropped" from the original. So
redeclaring a class this way is additive at the *module* level (new top-level names and
untouched classes are unaffected) but means defining the shadow class's *entire*
member set yourself, not just the members you want to change — on top of it still not
being the type the rest of the stdlib actually resolves to. Using this for a mutable
type like `list`/`dict`/`set` would therefore mean copying that class's *entire* member
set from real typeshed into the shadow, modifying only the signatures that need
`Mut`-awareness (e.g. `list.append` taking a `Mut`-aware element type when the list
itself is `Mut[list[Mut[User]]]`) — moot anyway, since the shadow type is invisible to
every other stub that references the real `list`.

Neither approach was pursued to completion, since the shadow-type problem makes
`__builtins__.pyi` overrides unusable for the real goal regardless. The AST-filter
alternative (recognizing `list.append`-style calls as
construction-exemption cases in `mut_check._filter`) remains a viable fallback that
avoids tracking typeshed at all — worth weighing against this once someone actually
implements either.

## `ty` bug: `Self` doesn't substitute through a generic type alias (fixed in ty 0.0.85)

**Status (checked 2026-10-06):** fixed by astral-sh/ruff#28890 (commit `162c08c`, "Specialize
Self bounds through generic type aliases", fixes astral-sh/ty#4592) and **released in
`ty` 0.0.85** (2026-10-06; listed in its changelog). Confirmed against the real release,
not just a from-source build: the minimal repro below passes on 0.0.85 and still fails
on 0.0.84. This project now pins `ty==0.0.85`. The `Mut[S]` stub workaround stays in
place and remains correct -- reverting it back to `Mut[Self]` would be possible but has
no benefit, so it hasn't been touched.

`test_ty_rejects_mut_self_on_generic_class` and
`test_ty_still_rejects_self_in_intersection_on_mut_receiver` (`test_ty_bugs.py`), along
with the fixtures they pinned (`mut_self_generic_class_ty_bug.py`,
`mut_check_ty_bug_self_in_intersection.py`), were **removed**: both fail against the
fix, so there's nothing left to pin. While waiting for the release, this was exercised
through a machine-local `[tool.uv.sources]` override building `ty` from a patched
clone; that override is gone now that the pin is a real release.

**Mechanism** (traced through `ty`'s source and confirmed with debug output from a
from-source build, not just inferred from behavior). A bound method call passes the
receiver as a synthetic first argument, so `Self`'s declared upper bound matters
during inference. For a bare `self: Self`, accessing the method on `Box[int]` rewrites
that bound from `Box[T@Box]` to `Box[int]` (via `possibly_apply_to_self` in
`typevar.rs`) -- but only when the mapping being applied carries
`specialize_self_domain = true`. For `Mut[Self]`, the mapping reaches the alias's
stored arguments through `Specialization::apply_specialization_impl`
(`generics.rs`), which rebuilt the mapping with that flag hardcoded to `false`, so
`Self` kept the unspecialized bound `Box[T@Box]` and `Box[int]` failed the check
against it. Upstream's fix adds a `specialize_self_domain` parameter to that function
and passes the flag through from the alias arm in `type_alias.rs`. Same one-line idea
as the candidate patch worked out independently here, but changing the existing
function's signature instead of adding a parallel helper -- the shape a maintainer
would (and did) prefer.

**Original framing** (kept for the trail). Originally found and framed as "`Self` inside
`Intersection` doesn't substitute" while vendoring the patched typeshed fork's
`list` stub — **that framing turned out to be wrong, or at least too narrow**, per a
later, more careful isolation (see the "Narrower root cause" subsection below). Kept
here under its corrected name.

**Original symptom, already fixed in our stubs**, see the comment above `list`'s
`S = TypeVar("S", bound="list")`: any method declared `self: Mut[Self]` on a
parameterized `list[_T]` gets rejected for both `Mut[list[int]]` and plain
`list[int]` receivers. Worked around project-wide by using an explicit
`self: Mut[S]` (`S` bound to the unparameterized class) instead of `Self`, which the
ordinary constraint solver substitutes correctly. Applied to
`append`/`extend`/`pop`/`insert`/`remove`/`sort`/`__delitem__`/`__iadd__`, and
`__setitem__`'s first overload (which had been missed in the initial pass — its
`self: Mut[Self]` reproduced the same false rejection reported as "list[0] = 1
errors" from another session; fixed the same way).

### Narrower root cause (confirmed after the fact, isolating one variable at a time)

Minimal reproduction, no `Intersection`, no `ty_extensions` import, nothing project-
specific — just `Self` through the identity alias:

```python
from typing import Self

type Mut[T] = T

class Box[T]:
    def mutate(self: Mut[Self], value: T) -> None:
        pass

def f(b: Mut[Box[int]]) -> None:
    b.mutate(1)  # rejected -- should be accepted (Mut[T] = T, so this is just self: Self)
```

```
error[invalid-argument-type]: Argument to bound method `Box.mutate` is incorrect
 --> repro.py:9:5
  |
9 |     b.mutate(1)
  |     ^^^^^^^^^^^ Argument type `Box[int]` does not satisfy upper bound `Box[T@Box]` of type variable `Self`

Found 1 diagnostic
```

So it was never about `Intersection` — it's `Self`, used as the argument to *any*
PEP 695 generic type alias, applied to a *generic* class. `self: Self` directly (no
alias) on the same `Box[T]` is completely clean; `self: Intersection[Self, Marker]`
written inline (no alias) is also completely clean. Isolated one variable at a time:

- **Not about `Intersection` specifically** — the identity alias (`type Mut[T] = T`)
  reproduces it identically, no marker/intersection involved at all.
- **Not about the private, `Intersection`-based backend** — reproduces under plain
  `ty check` against the *public*, transparent `Mut[T] = T` alias real users' own
  checkers see, confirmed via `run_checker` (see `test_ty_rejects_mut_self_on_generic_class`
  in `test_ty_bugs.py`).
- **`reveal_type(self)` inside the method body shows `Self@mutate` (unresolved)** —
  not `Box[T@Box]`. The call-site diagnostic's "upper bound `Box[T@Box]`" is also
  itself unspecialized (`T@Box`, not `int`, despite the call being against
  `Box[int]`) — so it's not just that `Self` fails to pick up whatever `Mut` adds;
  the bound being checked against isn't even substituted with the call's own type
  arguments in the first place.
- **The alias mechanism itself only half-works, independent of `Self`**: `ty` only
  ever resolves `Intersection` through a `type`-statement (PEP 695) alias at all —
  confirmed a legacy alias (bare `TypeVar`-based assignment, or explicitly annotated
  `X: TypeAlias = Intersection[...]`) resolves to `@Todo` (`ty`'s own "not
  implemented" placeholder) unconditionally, regardless of genericity, `Self`, or
  what concrete type is plugged in (`Mut[int]`, `Mut[SomeNonGenericClass]`, even a
  fully non-generic alias definition with no subscripting at all — all `@Todo`).
  Since PEP 695 is the *only* alias form that resolves `Intersection` in the first
  place, there's no alias-style choice that sidesteps the `Self` bug; `type Mut[T]
  = Intersection[T, MutMarker]` isn't one option among several, it's the only one
  that works at all.
- **Defining a per-class alias in the class body is a dead end, and a worse one**:
  `type MutSelf = Mut[Self]` inside `class Box[T]:` hits a *different*, harder error
  first — `ty` rejects `Self` inside any type alias outright
  (`error[invalid-type-form]: Self cannot be used in a type alias`) — and the
  fallback isn't neutral: `MutSelf` degrades to `Unknown & Marker`, and `Unknown`
  accepts anything, so it stops discriminating "is this actually a `Box`" at all,
  not just "is `T` right." Strictly less sound than the original bug, not a
  workaround.

**No workaround found for the `Self`-in-generic-alias case beyond what's already in
the stub** (`self: Mut[S]`, `S` a bound `TypeVar`, instead of `Self`) — that
continues to be correct and necessary, not something this later investigation
changes.

**Test coverage gap this exposed**: none of this project's own hand-written `Self`-
gating fixtures (`mut_self_mypy_bug.py`, `mut_check_self_requires_mut_*.py`) ever
used a generic class — all of them use the same non-generic `Counter` — so this bug
was invisible to the test suite entirely until the stdlib container stubs (the only
place a generic class + `Mut[Self]`/`Mut[S]` combination was actually exercised)
surfaced it. `test_ty_bugs.py`'s `test_ty_rejects_mut_self_on_generic_class` (public
alias, plain `ty check`) and `test_ty_still_rejects_self_in_intersection_on_mut_receiver`
(private backend) now pin both shapes directly.

## Open `ty` bug: subscript syntax doesn't honor `Mut[S]` on `__getitem__`/`__setitem__`

**Status (2026-09-25):** still open. A `ty` developer is reportedly already working on
a fix (relayed second-hand; no issue or PR link recorded here), and it looks more
involved than the `Self` bug above -- so nothing to do on this side but wait for a
release and then re-run `test_ty_still_rejects_subscript_assignment_on_mut_receiver`.
Still reproduces on `ty` 0.0.84 with a minimal, project-free repro (an `Intersection`
receiver with an explicit `self: Intersection[Box[T], Marker]` `__setitem__`, called
via `b[0] = 1`, rejected while `b.__setitem__(0, 1)` is accepted). When it does get
fixed, re-verify all three cases from the reverted-exemption trail below -- not just the
one in the pin test -- before reintroducing any `mut_check`-layer handling.

**Likely mechanism (read from `ty`'s source at `85d0b3f`; not instrumented or
confirmed by a build, unlike the `Self` bug above -- treat as a well-supported
hypothesis).** `validate_subscript_assignment_impl`
(`types/infer/builder/subscript.rs`) has its own `Type::Intersection` branch that
decomposes the receiver into its positive members and recurses on each one alone
(`object_ty = *element_ty`), OR-ing the results, *before* reaching the generic path that
calls `infer_and_try_call_dunder`. By then the full intersection is gone, so neither
`list[int]` alone (no `MutMarker`) nor `MutMarker` alone (no `__setitem__`) can satisfy
a `self: Mut[S]` receiver. Ordinary calls avoid this because
`Type::member_lookup_with_policy`'s intersection handling iterates members only to
*locate* a method while keeping `receiver = this` (the whole intersection) for binding,
and `del xs[0]` avoids it because it goes through `try_call_dunder_with_policy`, which
delegates intersections to `IntersectionType`'s own dunder handling -- consistent with
the empirical finding that `del` is unaffected. No existing `mdtest` covers
`Intersection` combined with subscript assignment, so nothing pins the decomposition's
intent.

**Confirmed on `ty` 0.0.82, still reproduces on 0.0.85 (2026-10-06)**, found alongside the bug above while vendoring the
patched typeshed fork's `list` stub — a separate bug, unrelated to `Self`
substitution. Even after fixing `__setitem__` to `self: Mut[S]`, `xs[0] = 1` on a
genuinely `Mut[list[int]]` receiver (parameter or `Mut`-declared local) is still
rejected: `invalid-assignment`, "Invalid subscript assignment ... on object of type
`list[int]`", with an info line correctly showing "The full type of the subscripted
object is `Mut[list[int]]`" — `ty` prints the right type and rejects it anyway.
Calling the same method explicitly, `xs.__setitem__(0, 1)`, type-checks clean on the
identical receiver, confirming the stub signature itself is correct and the bug is
specifically in how `ty`'s subscript-assignment special form resolves overloads
against an `Intersection` self type, not in the method signature.

Tested the read side too, deliberately, as a probe (not a real fix candidate —
`__getitem__` shouldn't require `Mut` for a read at all, and the stub was reverted
after testing): adding `self: Mut[S]` to `__getitem__`'s overloads makes
`x: int = xs[0]` fail on *both* `Mut[list[int]]` and plain `list[int]` receivers,
with a different, worse error — `Method __getitem__ of type Overload[]` — `ty` can't
resolve an overload at all, rather than degrading to a self-type mismatch like
`__setitem__` does. Confirms the same root cause (subscript-form overload
resolution vs. `Mut`-gated `self`) hits both the get and set directions.

Also tried spelling `self` as the raw `Intersection[S, MutMarker]` instead of the
`Mut[S]` alias, in case the alias indirection itself was the problem -- no change.
`reveal_type` confirms it resolves to the identical effective type (`list[int] &
MutMarker`), and the explicit-call form still works either way; `xs[0] = 1` still
fails identically. Rules out the alias as a factor -- confirmed the bug is in
`ty`'s subscript-assignment special-casing itself, not in how the intersection
type is spelled.

**Net effect**: `xs[0] = 1` cannot currently be made to type-check under our
backend no matter how the stub is written, for a receiver that should legitimately
permit it. Blocks the natural syntax for indexed mutation entirely; the only
working spelling is the explicit dunder call, which isn't viable as real guidance.

**A `mut_check`-layer suppression (like `_filter`/`_immutable`'s) was tried and
reverted -- confirmed unsound, not just incomplete.** The idea: key off `ty`'s own
confirming info line, "The full type of the subscripted object is `Mut[...]`"
(present, confirmed, only when the receiver's declared type actually includes
`Mut` -- a plain, correctly-rejected receiver never produces it, checked directly
including through an attribute chain). That line only speaks to the *receiver's*
permission, though, and `ty`'s subscript-assignment resolution turns out to be
broken wholesale once the receiver carries `MutMarker` -- it doesn't get far enough
to validate the *assigned value* at all in that case, so a genuinely bad assignment
produces the exact same diagnostic shape as the false positive. Confirmed three
ways, escalating: `l[0] = user` where `l: Mut[list[Mut[User]]]` and `user: User`
(plain -- should reject on the *element* not carrying `Mut`, per "container
mutability is compositional") got silently swept up alongside the legitimate
`l[0] = mut_user` case; then, worse, `xs[0] = "wrong type"` where
`xs: Mut[list[int]]` -- an ordinary, `Mut`-unrelated type mismatch with nothing to
do with permissions at all -- also vanished. Suppressing on this signal doesn't
distinguish "only rejected because of the bug" from "correctly rejected" because
`ty` itself can't reach that determination once this path is taken; there is no
textual signal in the diagnostic to recover it from after the fact. Reverted
in full (the `mut_check._subscript` module, its wiring, and the fixtures/tests
that went with it) rather than shipped in a narrower, still-unsound form.
Explicit dunder calls remain the only sound spelling for subscript-assignment on
a `Mut`-typed receiver until `ty` fixes this upstream -- not added to CLAUDE.md's
"Open" list as actionable, since there's no known-safe next step, only "wait on
upstream `ty`."

## Untyped-code handling — how the modes were chosen

Modeled after mypy's closest real precedent (`--check-untyped-defs` /
`--disallow-untyped-defs` / per-module `ignore_errors`), not `ty`'s — `ty` itself has
no equivalent concept at all (confirmed: `ty check --help` exposes no
strict/untyped-body flag; its gradual typing is unconditional, with no config knob to
change it).

For the only custom pass that exists today (`_reassignment`), `"ignored"` and
`"permissive"` report identically for a file with zero annotations anywhere: zero
annotations trivially means zero `Mut` annotations, so the per-scope gate already
empties it out on its own. The two modes only diverge in whether the file's AST is
walked at all, not in what's reported — a real distinction once a future custom pass
exists whose behavior differs for "typed but `Mut`-less" vs. "no types at all" (e.g. an
attribute-write check might reasonably still want to inspect a typed-but-`Mut`-less
class even where `"permissive"` would otherwise skip it).

Config-file support (`../pyproject.toml`/`ty.toml`-style) is deliberately deferred until
the CLI flag's shape has proven itself, even though `ty` itself reads config from
exactly that kind of file.
