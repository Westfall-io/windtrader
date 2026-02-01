"""windtrader

Top-level package for the Python wrapper around the `windtrader-java` validator.

This package exposes a small, stable public API for validating SysML v2 textual
documents using the published `windtrader-java` shaded JAR. The Python wrapper
handles locating/downloading a pinned Java validator artifact, invoking the
JAR as a subprocess, and returning a structured `ValidationResult`.

Public API:
- `ValidationResult` : dataclass describing outcome and captured stdout/stderr.
- `WindtraderValidator` : thin object wrapper for running the Java validator.
- `validate()` : convenience function to validate text in one call.
- `validate_across_versions()` : run the same text against multiple Java versions.

The package version string is provided in `__version__`.
"""

from .validator import (
    ValidationResult,
    WindtraderValidator,
    validate,
    validate_across_versions,
)

__all__ = [
    "ValidationResult",
    "WindtraderValidator",
    "validate",
    "validate_across_versions",
]

__version__ = "0.1.0"
