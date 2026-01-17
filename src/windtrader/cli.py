# src/windtrader/cli.py
from __future__ import annotations

import argparse
import sys

from .validator import validate
from . import __version__


def main(argv: list[str] | None = None) -> int:
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
        help="windtrader-java version to use",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="timeout in seconds",
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
