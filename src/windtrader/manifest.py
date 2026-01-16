from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

from importlib import resources


@dataclass(frozen=True)
class ValidatorSpec:
    version: str
    jar: str
    java_min: int = 21
    args: List[str] = None


@dataclass(frozen=True)
class Manifest:
    latest: str
    validators: List[ValidatorSpec]

    def get(self, version: str) -> ValidatorSpec:
        for v in self.validators:
            if v.version == version:
                return v
        raise KeyError(f"Validator version not found in manifest: {version}")

    def ordered_versions_latest_first(self) -> List[str]:
        # Keep the manifest order stable but ensure latest is first
        versions = [v.version for v in self.validators]
        if self.latest in versions:
            versions.remove(self.latest)
            versions.insert(0, self.latest)
        return versions


def load_manifest() -> Manifest:
    pkg = "windtrader.validators"
    name = "manifest.json"
    with resources.files(pkg).joinpath(name).open("rb") as f:
        data = json.load(f)

    validators: List[ValidatorSpec] = []
    for item in data.get("validators", []):
        validators.append(
            ValidatorSpec(
                version=item["version"],
                jar=item["jar"],
                java_min=int(item.get("java_min", 21)),
                args=list(item.get("args", [])),
            )
        )

    return Manifest(latest=data["latest"], validators=validators)


def get_validator_jar_path(jar_filename: str):
    # Returns a Traversable; convert to real path via as_file() when executing.
    return resources.files("windtrader.validators").joinpath(jar_filename)