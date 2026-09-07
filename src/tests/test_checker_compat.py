"""
Compatibility: users' own checkers must only see the transparent `Mut[T] = T` alias.

`ty` here means a *plain* `ty` invocation — no `extra-paths` override pointed at
`stubs/internal/`. That override is exclusively for the tool's own bundled `ty`
process; a user's local `ty` install (or this repo's own dev-tooling `ty`) must
resolve `immutablepy` the same way mypy/pyright do, and therefore must not
report any diagnostic caused by `Mut[T]`.
"""

import pytest
from _checkers import CHECKERS, FIXTURES_DIR, run_checker

FIXTURE = FIXTURES_DIR / "mut_usage.py"


@pytest.mark.parametrize("checker_args", CHECKERS)
def test_checker_reports_no_errors(checker_args: list[str]) -> None:
    result = run_checker(checker_args, FIXTURE)

    assert result.returncode == 0, result.stdout + result.stderr
