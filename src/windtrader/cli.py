"""
windtrader CLI.

Provides the `windtrader` command-line interface for driving the `windtrader-java`
backend: `check` (parse-only validation), `echo`, and `export` (element JSON graph).

Usage model
-----------
- The CLI reads SysML text from stdin.
- It invokes the Java backend jar (`windtrader-java`) via the Python client.
- It forwards stdout/stderr from the Java tool verbatim.
- It exits with the same exit code as the Java tool.

Subcommands
-----------
- `check` (default): parse-validate SysML text.
- `echo`: print the normalized/echoed representation.
- `export`: parse SysML and print the SysMLv2 element JSON graph (API shape).

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
from ._jars import DEFAULT_VERSION
from .client import echo as client_echo
from .client import export as client_export
from .client import validate


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
        The exit code returned by the Java backend process.

    Behavior
    --------
    - Reads all input from stdin (blocking until EOF).
    - Runs the selected subcommand with the provided Java backend version and timeout.
    - Writes any backend stdout to stdout and stderr to stderr (verbatim).
    - Returns the backend exit code.
    """
    p = argparse.ArgumentParser(
        prog="windtrader",
        description="SysML v2 wrapper around windtrader-java (check / echo / export)",
    )

    # Standard CLI version flag (prints Python package version)
    p.add_argument(
        "--version",
        action="version",
        version=f"windtrader {__version__}",
    )

    p.add_argument(
        "subcommand",
        nargs="?",
        default="check",
        choices=["check", "echo", "export"],
        help="backend subcommand to run (default: check)",
    )

    # Java backend configuration
    p.add_argument(
        "--java-version",
        default=DEFAULT_VERSION,
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

    if args.subcommand == "export":
        res = client_export(text, version=args.java_version, timeout_s=args.timeout)
    elif args.subcommand == "echo":
        res = client_echo(text, version=args.java_version, timeout_s=args.timeout)
    else:
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
