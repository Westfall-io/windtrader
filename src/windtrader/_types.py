from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


"""Type definitions used by the windtrader wrapper.

This module provides lightweight dataclasses that represent the structured
results returned by the validator wrapper. Keeping these small and immutable
makes them convenient to pass around in tests and callers.
"""


@dataclass(frozen=True)
class ValidationError:
    """A single syntax/parse error reported by the validator.

    Attributes
    ----------
    line:
        1-based line number where the error occurred, or `None` when unknown.
    offset:
        Character offset on the line where the error was detected, or `None`.
    near:
        Short snippet of text near the error (best-effort) or `None`.
    msg:
        Human-readable message from the validator describing the issue.
    """

    line: Optional[int]
    offset: Optional[int]
    near: Optional[str]
    msg: Optional[str]


@dataclass(frozen=True)
class ValidationResult:
    """Result summary returned after invoking the Java validator.

    Attributes
    ----------
    ok:
        True when the validator exited with code 0.
    jar_label:
        Label describing the JAR used (e.g. a human label like "latest" or a
        version string such as "0.1.1").
    jar_path:
        Local filesystem path to the jar that was executed.
    exit_code:
        Process exit code returned by the validator.
    errors:
        List of `ValidationError` objects representing parse diagnostics.
    raw_stderr:
        Raw stderr output captured from the Java process.
    raw_stdout:
        Raw stdout output captured from the Java process.
    """

    ok: bool
    jar_label: str  # e.g., "latest" or "0.56.0-..."
    jar_path: str
    exit_code: int
    errors: list[ValidationError]
    raw_stderr: str
    raw_stdout: str


@dataclass(frozen=True)
class CrossVersionResult:
    """Container for results when validating across multiple versions.

    Attributes
    ----------
    latest:
        `ValidationResult` produced by validating with the "latest" (or first)
        target version.
    compatible:
        Optionally, a `ValidationResult` for a previously-tested version that
        was found to be compatible (or `None` if none passed).
    """

    latest: ValidationResult
    compatible: Optional[ValidationResult]  # a previous version that passes, if any
