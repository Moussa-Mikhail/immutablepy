# IDE-only shim, not used by any checker.
#
# `ty_extensions` is synthetic: it's resolved specially by the real `ty`
# binary via its own vendored typeshed, not a real installable module. No
# PyPI package actually provides it (the "ty-extensions" package on PyPI is
# an unrelated squat). PyCharm's own inspector has no notion of `ty`'s
# special-cased resolution, so `from ty_extensions import Intersection` in
# stubs/internal/immutablepy/__init__.pyi always reads as unresolved to it.
#
# This file exists only so PyCharm's source roots (see immutablepy.iml) have
# something real to resolve that name against. It mirrors the subset of
# ty's actual vendored stub (`ty_extensions.pyi` in ty's typeshed) that this
# project uses. The real bundled `ty` ignores this file entirely -- it
# always uses its own built-in vendored definition.
# noinspection protected-member
from typing import _SpecialForm

Intersection: _SpecialForm
