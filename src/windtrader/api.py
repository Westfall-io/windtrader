from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .errors import (
    InvalidAllVersions,
    InvalidLatestButValidOnOlder,
    SysmlInvalidError,
    ValidatorRuntimeError,
)
from .jar_runner import run_validator
from .manifest import load_manifest


@dataclass(frozen=True)
class CompatibilityReport:
    latest_version: str
    status: str  # valid_latest | valid_old_only | invalid_all | validator_error
    valid_versions: List[str]
    invalid_versions: Dict[str, str]  # version -> short stderr
    runtime_errors: Dict[str, str]    # version -> error msg


def available_versions() -> List[str]:
    m = load_manifest()
    return [v.version for v in m.validators]


def latest_version() -> str:
    return load_manifest().latest


def validate(text: str, *, version: str) -> None:
    m = load_manifest()
    spec = m.get(version)
    r = run_validator(text, spec)
    if r.ok:
        return
    # returncode != 0 => invalid or runtime error; treat nonzero as invalid SysML unless clearly runtime
    # (If you later standardize exit codes, we can split them cleanly.)
    raise SysmlInvalidError(f"Invalid SysML for validator {version}.\n{r.stderr.strip()}")


def validate_latest(text: str) -> None:
    validate(text, version=latest_version())


def compatibility_report(text: str) -> CompatibilityReport:
    m = load_manifest()
    latest = m.latest
    valid_versions: List[str] = []
    invalid_versions: Dict[str, str] = {}
    runtime_errors: Dict[str, str] = {}

    for ver in m.ordered_versions_latest_first():
        spec = m.get(ver)
        try:
            r = run_validator(text, spec)
        except ValidatorRuntimeError as e:
            runtime_errors[ver] = str(e)
            continue

        if r.ok:
            valid_versions.append(ver)
        else:
            invalid_versions[ver] = (r.stderr.strip() or f"returncode={r.returncode}")[:500]

    if latest in valid_versions:
        status = "valid_latest"
    elif valid_versions:
        status = "valid_old_only"
    elif runtime_errors and not invalid_versions:
        status = "validator_error"
    else:
        status = "invalid_all"

    return CompatibilityReport(
        latest_version=latest,
        status=status,
        valid_versions=valid_versions,
        invalid_versions=invalid_versions,
        runtime_errors=runtime_errors,
    )


def validate_with_compat(text: str) -> None:
    """
    Validate against latest. If it fails but is valid on older bundled versions,
    raise a targeted exception so callers can treat it as a migration case.
    """
    rep = compatibility_report(text)
    latest = rep.latest_version

    if rep.status == "valid_latest":
        return

    if rep.status == "valid_old_only":
        raise InvalidLatestButValidOnOlder(latest=latest, valid_versions=rep.valid_versions)

    if rep.status == "validator_error":
        raise ValidatorRuntimeError(f"Validator runtime error(s): {rep.runtime_errors}")

    raise InvalidAllVersions(latest=latest)
