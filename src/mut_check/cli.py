"""Command-line entry point for the `mut-check` script."""

import sys

from mut_check import check


def main() -> int:
    """Run the private static check against the paths given on the command line."""
    result = check(*sys.argv[1:])
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
