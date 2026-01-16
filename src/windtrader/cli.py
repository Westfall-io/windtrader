from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .api import available_versions, compatibility_report, validate, validate_latest, latest_version
from .errors import SysmlInvalidError, ValidatorRuntimeError


def _read_text(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(prog="windtrader")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("versions", help="List bundled validator versions")

    p_check = sub.add_parser("check", help="Validate SysML text (latest by default)")
    p_check.add_argument("file", nargs="?", default="-", help="SysML file path or '-' for stdin")
    p_check.add_argument("--version", default=None, help="Validator version to use")

    p_compat = sub.add_parser("compat", help="Check validity across versions and report compatibility")
    p_compat.add_argument("file", nargs="?", default="-", help="SysML file path or '-' for stdin")

    args = p.parse_args()

    try:
        if args.cmd == "versions":
            print("latest:", latest_version())
            for v in available_versions():
                print(v)
            return

        if args.cmd == "check":
            text = _read_text(args.file)
            if args.version:
                validate(text, version=args.version)
            else:
                validate_latest(text)
            return

        if args.cmd == "compat":
            text = _read_text(args.file)
            r = compatibility_report(text)
            print("status:", r.status)
            print("latest:", r.latest_version)
            if r.valid_versions:
                print("valid:", ", ".join(r.valid_versions))
            if r.invalid_versions:
                print("invalid:")
                for ver, msg in r.invalid_versions.items():
                    print(f"  - {ver}: {msg.splitlines()[0] if msg else ''}")
            if r.runtime_errors:
                print("runtime_errors:")
                for ver, msg in r.runtime_errors.items():
                    print(f"  - {ver}: {msg}")
            return

    except SysmlInvalidError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(2)
    except ValidatorRuntimeError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(3)
