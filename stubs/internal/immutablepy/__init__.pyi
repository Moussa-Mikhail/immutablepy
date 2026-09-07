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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from ty_extensions import Intersection

    class MutMarker: ...

    # noinspection type-hints
    type Mut[T] = Intersection[T, MutMarker]

    def mut_method[F: Callable[..., object]](method: F) -> F: ...
    def mut[T](value: T) -> Mut[T]: ...
