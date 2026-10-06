"""Async counterparts of the plain constructs `mut_check._reassignment` already
checks -- an `async def` parameter, an `async for` target, and an
`async with` target each bind a name exactly like their sync forms, so a
reassignment in the body is a violation without `Mut`. Each function opts
in via a `Mut` annotation of its own (`_opt_in`), per CLAUDE.md's
"Incremental adoption" ratchet.
"""

from immutablepy import Mut


async def async_parameter(_x: int) -> None:
    _opt_in: Mut[int] = 0
    _x = 5


async def async_for_target(items) -> None:
    _opt_in: Mut[int] = 0
    async for i in items:
        i += 1


async def async_with_target(manager) -> None:
    _opt_in: Mut[int] = 0
    async with manager as m:
        m += 1
