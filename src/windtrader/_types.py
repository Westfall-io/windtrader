from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationError:
    line: int | None
    offset: int | None
    near: str | None
    msg: str | None


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    jar_label: str  # e.g., "latest" or "0.56.0-..."
    jar_path: str
    exit_code: int
    errors: list[ValidationError]
    raw_stderr: str
    raw_stdout: str


@dataclass(frozen=True)
class CrossVersionResult:
    latest: ValidationResult
    compatible: ValidationResult | None  # a previous version that passes, if any
