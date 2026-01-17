# src/windtrader/cli.py
from __future__ import annotations

import argparse
import sys

from .validator import validate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="windtrader", description="SysML v2 parse-only validator wrapper")
    p.add_argument("--version", default="0.1.1", help="windtrader-java version to use")
    p.add_argument("--timeout", type=float, default=10.0, help="timeout in seconds")
    p.add_argument("--version", default="0.1.1", help="windtrader-java version")
    args = p.parse_args(argv)

    text = sys.stdin.read()
    res = validate(text, version=args.version, timeout_s=args.timeout)

    # Always forward tool output (keeps behavior simple and debuggable)
    if getattr(res, "stdout", ""):
        sys.stdout.write(res.stdout)
        if not res.stdout.endswith("\n"):
            sys.stdout.write("\n")

    if getattr(res, "stderr", ""):
        sys.stderr.write(res.stderr)
        if not res.stderr.endswith("\n"):
            sys.stderr.write("\n")

    # Exit code should match the java tool’s exit code (0 ok, 2 parse error, etc.)
    return int(getattr(res, "exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
