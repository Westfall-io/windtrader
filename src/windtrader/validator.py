from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import subprocess
import time

from ._jars import get_jar_path

DEFAULT_VERSION = "0.1.1"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    version: str
    exit_code: int
    stdout: str
    stderr: str
    jar_path: str
    duration_s: float

    @property
    def is_invalid_syntax(self) -> bool:
        # windtrader-java convention: 2 means "invalid SysML"
        return self.exit_code == 2

    @property
    def is_runtime_error(self) -> bool:
        return self.exit_code not in (0, 2)


class WindtraderValidator:
    """
    Thin wrapper around windtrader-java.

    We intentionally use the CLI contract:
      - `check` => exit 0 valid, exit 2 invalid, exit 3 runtime error
      - `echo`  => prints parsed text if valid
    """

    def __init__(self, version: str = DEFAULT_VERSION):
        self.version = version

    def validate_text(self, text: str, timeout_s: float = 10.0) -> ValidationResult:
        jar = get_jar_path(self.version)

        t0 = time.time()
        p = subprocess.run(
            ["java", "-jar", str(jar), "check"],
            input=text,
            text=True,
            capture_output=True,
            timeout=timeout_s,
        )
        t1 = time.time()

        return ValidationResult(
            ok=(p.returncode == 0),
            version=self.version,
            exit_code=p.returncode,
            stdout=p.stdout or "",
            stderr=p.stderr or "",
            jar_path=str(jar),
            duration_s=(t1 - t0),
        )

    def echo(self, text: str, timeout_s: float = 10.0) -> ValidationResult:
        jar = get_jar_path(self.version)

        t0 = time.time()
        p = subprocess.run(
            ["java", "-jar", str(jar), "echo"],
            input=text,
            text=True,
            capture_output=True,
            timeout=timeout_s,
        )
        t1 = time.time()

        return ValidationResult(
            ok=(p.returncode == 0),
            version=self.version,
            exit_code=p.returncode,
            stdout=p.stdout or "",
            stderr=p.stderr or "",
            jar_path=str(jar),
            duration_s=(t1 - t0),
        )

    def validate(self, text: str, timeout_s: float = 10.0) -> ValidationResult:
        return self.validate_text(text, timeout_s=timeout_s)


def validate(
    text: str, version: str = DEFAULT_VERSION, timeout_s: float = 10.0
) -> ValidationResult:
    return WindtraderValidator(version=version).validate_text(text, timeout_s=timeout_s)


def validate_across_versions(
    text: str,
    versions: Sequence[str],
    timeout_s: float = 10.0,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for v in versions:
        results.append(validate(text, version=v, timeout_s=timeout_s))
    return results
