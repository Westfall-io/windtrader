from __future__ import annotations

from ._jars import get_jar_path

from dataclasses import dataclass
from typing import Sequence

import subprocess
import time

"""
Python wrapper around the `windtrader-java` validator.

This module provides a small, stable API for validating SysML v2 text using the
published `windtrader-java` shaded jar.

Contract with windtrader-java
-----------------------------
We rely on the validator jar's CLI behavior:

- `java -jar <jar> check`
    Exit code:
      0 => syntax valid
      2 => syntax invalid (parse error)
      3 => runtime/tool error (or other non-parse failures)

- `java -jar <jar> echo`
    Prints a normalized/echoed representation when valid (implementation-defined).

These exit codes are intentionally preserved and surfaced to callers via ValidationResult.
"""


DEFAULT_VERSION = "0.1.1"


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of invoking `windtrader-java` on a text input.

    Attributes
    ----------
    ok:
        True when the tool exited with code 0.
    version:
        windtrader-java version string used to resolve/download the jar.
    exit_code:
        Process exit code returned by the jar.
    stdout:
        Captured standard output from the jar.
    stderr:
        Captured standard error from the jar (often contains diagnostics).
    jar_path:
        Local filesystem path to the jar used during this invocation.
    duration_s:
        Wall-clock runtime in seconds for the subprocess call.
    """

    ok: bool
    version: str
    exit_code: int
    stdout: str
    stderr: str
    jar_path: str
    duration_s: float

    @property
    def is_invalid_syntax(self) -> bool:
        """
        True if the input is syntactically invalid per windtrader-java.

        Convention: exit code 2 means "invalid SysML" (parse error).
        """
        return self.exit_code == 2

    @property
    def is_runtime_error(self) -> bool:
        """
        True if the tool failed for reasons other than a parse error.

        Convention:
        - 0 is success
        - 2 is invalid syntax
        Any other code indicates a tool/runtime failure (e.g., linkage errors).
        """
        return self.exit_code not in (0, 2)


class WindtraderValidator:
    """
    Thin wrapper around `windtrader-java`.

    This class is intentionally small. It:
    - resolves/downloads the correct jar for a given version
    - runs the jar with a bounded timeout
    - returns captured stdout/stderr + metadata as a ValidationResult
    """

    def __init__(self, version: str = DEFAULT_VERSION):
        """
        Parameters
        ----------
        version:
            windtrader-java version string to download/use. Defaults to DEFAULT_VERSION.
        """
        self.version = version

    def validate_text(self, text: str, timeout_s: float = 10.0) -> ValidationResult:
        """
        Validate SysML v2 text using `windtrader-java check`.

        Parameters
        ----------
        text:
            SysML v2 textual syntax to validate.
        timeout_s:
            Subprocess timeout in seconds.

        Returns
        -------
        ValidationResult
            Captures process exit code, stdout, stderr, jar path, and duration.
        """
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
        """
        Run `windtrader-java echo` on SysML v2 text.

        This is useful for debugging/parsing investigations because it returns the tool's
        "echoed" / normalized representation (implementation-defined by windtrader-java).

        Parameters
        ----------
        text:
            SysML v2 textual syntax to parse/echo.
        timeout_s:
            Subprocess timeout in seconds.

        Returns
        -------
        ValidationResult
            Captures process exit code, stdout, stderr, jar path, and duration.
        """
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
        """
        Convenience alias for validate_text().

        Kept for readability in user code and tests.
        """
        return self.validate_text(text, timeout_s=timeout_s)


def validate(
    text: str, version: str = DEFAULT_VERSION, timeout_s: float = 10.0
) -> ValidationResult:
    """
    Validate SysML v2 text in one call without instantiating WindtraderValidator.

    Parameters
    ----------
    text:
        SysML v2 textual syntax to validate.
    version:
        windtrader-java version string to download/use.
    timeout_s:
        Subprocess timeout in seconds.

    Returns
    -------
    ValidationResult
        Captures exit code, stdout, stderr, jar path, and duration.
    """
    return WindtraderValidator(version=version).validate_text(text, timeout_s=timeout_s)


def validate_across_versions(
    text: str,
    versions: Sequence[str],
    timeout_s: float = 10.0,
) -> list[ValidationResult]:
    """
    Validate the same SysML v2 text against multiple windtrader-java versions.

    Parameters
    ----------
    text:
        SysML v2 textual syntax to validate.
    versions:
        Iterable of windtrader-java version strings.
    timeout_s:
        Subprocess timeout for each version.

    Returns
    -------
    list[ValidationResult]
        One result per version, in the same order as `versions`.
    """
    results: list[ValidationResult] = []
    for v in versions:
        results.append(validate(text, version=v, timeout_s=timeout_s))
    return results
