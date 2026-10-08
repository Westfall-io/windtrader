from __future__ import annotations

import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass

from ._jars import DEFAULT_VERSION, get_jar_path

"""
Python client for the `windtrader-java` CLI (check / echo / export).

This module provides a small, stable API for driving the published
`windtrader-java` shaded jar from Python.

Contract with windtrader-java
-----------------------------
We rely on the jar's CLI behavior:

- `java -jar <jar> check`
    Exit code:
      0 => syntax valid
      2 => syntax invalid (parse error)
      3 => runtime/tool error (or other non-parse failures)

- `java -jar <jar> echo`
    Prints a normalized/echoed representation when valid (implementation-defined).

- `java -jar <jar> export`
    Parses SysML text and prints the SysMLv2 element JSON graph (API shape)
    to stdout. Exit codes:
      0 => exported JSON on stdout
      2 => invalid syntax (no JSON)
      3 => runtime/tool error (e.g. standard library unavailable)

These exit codes are intentionally preserved and surfaced to callers via CommandResult.
"""


@dataclass(frozen=True)
class CommandResult:
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


class WindtraderClient:
    """
    Thin client around `windtrader-java`.

    This class is intentionally small. It:
    - resolves/downloads the correct jar for a given version
    - runs the jar with a bounded timeout
    - returns captured stdout/stderr + metadata as a CommandResult
    """

    def __init__(self, version: str = DEFAULT_VERSION):
        """
        Parameters
        ----------
        version:
            windtrader-java version string to download/use. Defaults to DEFAULT_VERSION.
        """
        self.version = version

    def _run(self, subcommand: str, text: str, timeout_s: float) -> CommandResult:
        """Run the jar with the given subcommand on `text`, returning a CommandResult."""
        jar = get_jar_path(self.version)

        t0 = time.time()
        p = subprocess.run(
            ["java", "-jar", str(jar), subcommand],
            input=text,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        t1 = time.time()

        return CommandResult(
            ok=(p.returncode == 0),
            version=self.version,
            exit_code=p.returncode,
            stdout=p.stdout or "",
            stderr=p.stderr or "",
            jar_path=str(jar),
            duration_s=(t1 - t0),
        )

    def validate_text(self, text: str, timeout_s: float = 10.0) -> CommandResult:
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
        CommandResult
            Captures process exit code, stdout, stderr, jar path, and duration.
        """
        return self._run("check", text, timeout_s)

    def echo(self, text: str, timeout_s: float = 10.0) -> CommandResult:
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
        CommandResult
            Captures process exit code, stdout, stderr, jar path, and duration.
        """
        return self._run("echo", text, timeout_s)

    def export(self, text: str, timeout_s: float = 30.0) -> CommandResult:
        """
        Run `windtrader-java export` on SysML v2 text.

        On success (exit 0) `stdout` holds the SysMLv2 element JSON graph (an
        array of API-shaped elements). On invalid input (exit 2) no JSON is
        emitted and `stderr` carries the parse diagnostics. On runtime failure
        (exit 3, e.g. standard library unavailable) nothing valid is emitted.

        Parameters
        ----------
        text:
            SysML v2 textual syntax to export to its element JSON graph.
        timeout_s:
            Subprocess timeout in seconds (default higher than check/echo because
            export loads the standard library and runs resolve/transform).

        Returns
        -------
        CommandResult
            Captures process exit code, stdout (JSON), stderr, jar path, and duration.
        """
        return self._run("export", text, timeout_s)

    def validate(self, text: str, timeout_s: float = 10.0) -> CommandResult:
        """
        Convenience alias for validate_text().

        Kept for readability in user code and tests.
        """
        return self.validate_text(text, timeout_s=timeout_s)


def validate(text: str, version: str = DEFAULT_VERSION, timeout_s: float = 10.0) -> CommandResult:
    """
    Validate SysML v2 text in one call without instantiating WindtraderClient.

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
    CommandResult
        Captures exit code, stdout, stderr, jar path, and duration.
    """
    return WindtraderClient(version=version).validate_text(text, timeout_s=timeout_s)


def echo(text: str, version: str = DEFAULT_VERSION, timeout_s: float = 10.0) -> CommandResult:
    """
    Echo SysML v2 text in one call without instantiating WindtraderClient.

    Returns
    -------
    CommandResult
        Captures exit code, stdout, stderr, jar path, and duration.
    """
    return WindtraderClient(version=version).echo(text, timeout_s=timeout_s)


def export(text: str, version: str = DEFAULT_VERSION, timeout_s: float = 30.0) -> CommandResult:
    """
    Export SysML v2 text to its element JSON graph in one call.

    On success (exit 0) `stdout` holds the SysMLv2 element JSON graph.

    Returns
    -------
    CommandResult
        Captures exit code, stdout (JSON), stderr, jar path, and duration.
    """
    return WindtraderClient(version=version).export(text, timeout_s=timeout_s)


def validate_across_versions(
    text: str,
    versions: Sequence[str],
    timeout_s: float = 10.0,
) -> list[CommandResult]:
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
    list[CommandResult]
        One result per version, in the same order as `versions`.
    """
    results: list[CommandResult] = []
    for v in versions:
        results.append(validate(text, version=v, timeout_s=timeout_s))
    return results
