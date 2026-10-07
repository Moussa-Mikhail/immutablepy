"""
Internal-only stub, never shipped to users.

Fed to the tool's private, pinned `ty` binary via `extra-paths` so that it
resolves the `immutablepy` module to this intersection-based definition
instead of the plain public one in `src/immutablepy/__init__.py`. This is
what lets `ty` natively enforce `Mut[T] <: T` (a `Mut[T]` value is accepted
where `T` is expected) while the value still preserves the type through
generic substitution and inheritance.

The reverse direction — plain `T` rejected where `Mut[T]` is expected because
it lacks `MutMarker` — is a real `ty` diagnostic that the tool's custom filter
suppresses, since plain values should satisfy `Mut` positions in this system.
"""

from collections.abc import Callable
from types import FunctionType, MethodType

from ty_extensions import Intersection

class MutMarker:
    # Fields inherit mutability from their owner: attribute access on a
    # `Mut[T]` (`T & MutMarker`) resolves through this `__getattr__` too, so
    # `o.field` is `declared & MutMarker` (and plain `declared` on a plain `T`).
    #
    # The union is load-bearing. A bound method and a `MutMarker` instance are
    # disjoint, so a bare `-> MutMarker` collapses every method to `Never` and
    # silently disables call checking on `Mut` receivers. `MethodType` keeps
    # instance methods and `FunctionType` keeps static/class methods; both are
    # `@final`, so they stay disjoint from data attributes and drop out.
    # `Callable[..., object]` does not work: it leaves a residue on everything.
    # Side effect: an unknown attribute on a `Mut` owner no longer raises
    # `unresolved-attribute` here (the plain checkers still do).
    def __getattr__(self, name: str) -> MutMarker | MethodType | FunctionType: ...

# noinspection type-hints
type Mut[T] = Intersection[T, MutMarker]

def mut_method[F: Callable[..., object]](method: F) -> F: ...
def mut[T](value: T) -> Mut[T]: ...
