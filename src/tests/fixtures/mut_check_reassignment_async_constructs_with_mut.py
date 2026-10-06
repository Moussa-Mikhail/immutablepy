"""Control case: the same mutations as mut_check_reassignment_async_constructs.py,
but each name is declared `Mut[...]` -- permitted. The `async def` parameter
is annotated directly; the `async for`/`async with` targets are pre-declared
(a bare `AnnAssign`), same shape as the sync
mut_check_reassignment_loop_var_with_mut.py.
"""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager

from immutablepy import Mut


async def async_parameter(_x: Mut[int]) -> None:
    _x = 5


async def async_for_target(items: AsyncIterator[int]) -> None:
    i: Mut[int]
    async for i in items:
        i += 1


async def async_with_target(manager: AbstractAsyncContextManager[int]) -> None:
    m: Mut[int]
    async with manager as m:
        m += 1
