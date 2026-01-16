from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


class WindtraderError(Exception):
    """Base exception for windtrader."""


@dataclass
class ValidatorResult:
    version: str
    ok: bool
    returncode: int
    stdout: str
    stderr: str


class ValidatorRuntimeError(WindtraderError):
    """The validator could not run reliably (Java missing, jar missing, timeout, etc.)."""


class SysmlInvalidError(WindtraderError):
    """Invalid SysML for the requested version."""


class InvalidLatestButValidOnOlder(SysmlInvalidError):
    def __init__(self, *, latest: str, valid_versions: Sequence[str], message: Optional[str] = None):
        msg = message or (
            f"Invalid on latest validator ({latest}), but valid on older version(s): {', '.join(valid_versions)}"
        )
        super().__init__(msg)
        self.latest = latest
        self.valid_versions = list(valid_versions)


class InvalidAllVersions(SysmlInvalidError):
    def __init__(self, *, latest: str, message: Optional[str] = None):
        msg = message or f"Invalid SysML for all bundled validator versions (latest={latest})."
        super().__init__(msg)
        self.latest = latest
