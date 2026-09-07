"""`mut_method` must preserve the decorated method's real type signature.

If it erased the signature (e.g. widening it to `Callable[..., Any]`), the
"bad" fixtures below — a wrong argument type and a wrong return-type use —
would type-check with zero complaints under every checker. They must not.
"""

import pytest
from _checkers import CHECKERS, FIXTURES_DIR, run_checker

OK_FIXTURE = FIXTURES_DIR / "mut_method_signature_ok.py"
BAD_ARG_FIXTURE = FIXTURES_DIR / "mut_method_signature_bad_arg.py"
BAD_RETURN_FIXTURE = FIXTURES_DIR / "mut_method_signature_bad_return.py"


@pytest.mark.parametrize("checker_args", CHECKERS)
def test_correct_usage_is_clean(checker_args: list[str]) -> None:
    result = run_checker(checker_args, OK_FIXTURE)

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("checker_args", CHECKERS)
def test_wrong_argument_type_is_flagged(checker_args: list[str]) -> None:
    result = run_checker(checker_args, BAD_ARG_FIXTURE)

    assert result.returncode != 0, "checker accepted str where add() expects int -- signature was erased"


@pytest.mark.parametrize("checker_args", CHECKERS)
def test_wrong_return_usage_is_flagged(checker_args: list[str]) -> None:
    result = run_checker(checker_args, BAD_RETURN_FIXTURE)

    assert result.returncode != 0, "checker accepted int assigned to str -- return type was erased"
