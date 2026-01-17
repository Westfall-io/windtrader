from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ValidationError:
    line: Optional[int]
    offset: Optional[int]
    near: Optional[str]
    msg: Optional[str]


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
    compatible: Optional[ValidationResult]  # a previous version that passes, if any
