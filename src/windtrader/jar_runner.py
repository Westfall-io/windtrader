from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from importlib.resources import as_file

from .errors import ValidatorResult, ValidatorRuntimeError
from .manifest import ValidatorSpec, get_validator_jar_path


@dataclass(frozen=True)
class RunOptions:
    timeout_seconds: int = 20


def _require_java() -> str:
    java = shutil.which("java")
    if not java:
        raise ValidatorRuntimeError(
            "Java runtime not found on PATH. Install a JRE/JDK (recommended: Java 21+) and retry."
        )
    return java


def run_validator(text: str, spec: ValidatorSpec, *, opts: Optional[RunOptions] = None) -> ValidatorResult:
    opts = opts or RunOptions()
    java = _require_java()

    jar_trav = get_validator_jar_path(spec.jar)
    args: List[str] = spec.args or []

    try:
        with as_file(jar_trav) as jar_path:
            cmd = [java, "-jar", str(jar_path), *args]
            p = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                timeout=opts.timeout_seconds,
            )
    except subprocess.TimeoutExpired as e:
        raise ValidatorRuntimeError(f"Validator timed out after {opts.timeout_seconds}s: {spec.version}") from e
    except FileNotFoundError as e:
        raise ValidatorRuntimeError(f"Validator jar not found: {spec.jar}") from e
    except Exception as e:
        raise ValidatorRuntimeError(f"Failed to run validator for {spec.version}: {e}") from e

    return ValidatorResult(
        version=spec.version,
        ok=(p.returncode == 0),
        returncode=p.returncode,
        stdout=p.stdout or "",
        stderr=p.stderr or "",
    )
