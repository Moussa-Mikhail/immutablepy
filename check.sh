#!/bin/bash
# shellcheck disable=SC2086

set -euo pipefail
cd "$(dirname "$0")"

# intentional word-splitting: the glob below must
# expand to multiple arguments, and it's deliberately non-recursive so it
# never descends into src/tests/fixtures/ (fixtures are deliberately broken
# code for other tests' sake; checking them here would fail on purpose).
to_check="src/immutablepy src/mut_check src/tests/*.py"

uv run ty check $to_check
uv run ruff check src
uv run immut check $to_check
uv run pytest
