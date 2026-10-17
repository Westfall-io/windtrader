from .client import (
    CommandResult,
    WindtraderClient,
    echo,
    export,
    validate,
    validate_across_versions,
)

__all__ = [
    "CommandResult",
    "WindtraderClient",
    "echo",
    "export",
    "validate",
    "validate_across_versions",
]

# Single-sourced from the distribution metadata so `__version__` can never drift
# from pyproject.toml's [project] version again (regression: 0.2.0 hardcoded here
# while the dist was 0.2.1 broke test_package_version_is_reported and the CLI
# --version). When not installed (e.g. a bare source checkout), fall back to a
# placeholder so importing windtrader never raises.
from importlib.metadata import PackageNotFoundError, version as _dist_version

try:
    __version__ = _dist_version("sysml-windtrader")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0+src"
