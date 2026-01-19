"""
windtrader CLI.

This module provides the `windtrader` command-line interface for validating SysML v2
text using the `windtrader-java` backend.

Usage model
-----------
- The CLI reads SysML text from stdin.
- It invokes the Java validator jar (`windtrader-java`) via the Python wrapper.
- It forwards stdout/stderr from the Java tool verbatim.
- It exits with the same exit code as the Java tool.

Exit codes (as defined by windtrader-java)
------------------------------------------
- 0: Valid SysML (parse succeeded)
- 2: Invalid SysML (syntax/parse error)
- 3: Runtime error (tool failure)
- Any other non-zero: Unexpected failure

Notes
-----
- `--version` prints the Python package version (not the Java backend version).
- Use `--java-version` to select which `windtrader-java` release asset to download/use.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .validator import validate


def main(argv: list[str] | None = None) -> int:
    """
    Entry point for the `windtrader` CLI.

    Parameters
    ----------
    argv:
        Optional argument list (excluding program name). If None, arguments are read
        from `sys.argv` (the default argparse behavior).

    Returns
    -------
    int
        The exit code returned by the Java validator process.

    Behavior
    --------
    - Reads all input from stdin (blocking until EOF).
    - Calls the validator with the provided Java backend version and timeout.
    - Writes any validator stdout to stdout and stderr to stderr (verbatim).
    - Returns the validator exit code.
    """
    p = argparse.ArgumentParser(
        prog="windtrader",
        description="SysML v2 parse-only validator wrapper",
    )

    # Standard CLI version flag (prints Python package version)
    p.add_argument(
        "--version",
        action="version",
        version=f"windtrader {__version__}",
    )

    # Java backend configuration
    p.add_argument(
        "--java-version",
        default="0.1.1",
        help="windtrader-java version to use (GitHub release asset version)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="timeout in seconds for the Java subprocess",
    )

    args = p.parse_args(argv)

    text = sys.stdin.read()
    res = validate(text, version=args.java_version, timeout_s=args.timeout)

    # Forward tool output verbatim
    if res.stdout:
        sys.stdout.write(res.stdout)
        if not res.stdout.endswith("\n"):
            sys.stdout.write("\n")

    if res.stderr:
        sys.stderr.write(res.stderr)
        if not res.stderr.endswith("\n"):
            sys.stderr.write("\n")

    # Match Java tool exit codes
    return int(res.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
