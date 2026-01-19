"""
windtrader._jars

Utilities for locating, downloading, and caching the `windtrader-java` validator JAR.

This module is intentionally dependency-free (stdlib only) so the Python wrapper can
remain lightweight while still fetching the pinned Java validator from GitHub Releases.

Key behavior:
- Determine a local cache directory (default: `~/.cache/windtrader`, overridable via env).
- Resolve the expected JAR cache path for a requested version.
- Attempt to download the JAR from a small set of candidate release URLs.
- Cache the JAR on disk so subsequent validations do not hit the network.

Environment variables:
- WINDTRADER_CACHE_DIR:
    Override the root cache directory where downloaded JARs are stored.
- WINDTRADER_JAVA_REPO:
    Override the GitHub repo used to fetch JARs (default: "Westfall-io/windtrader-java").
- WINDTRADER_JAVA_STABLE_ASSET:
    Optional: a fully-qualified URL to a stable asset (first-choice download target).
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

DEFAULT_REPO = "Westfall-io/windtrader-java"
DEFAULT_VERSION = "0.1.1"  # Default validator version used when none is provided.


def _cache_dir() -> Path:
    """
    Return the base cache directory for windtrader artifacts.

    By default this is `~/.cache/windtrader` on Unix-like systems. Users can override
    the location using the `WINDTRADER_CACHE_DIR` environment variable.

    Returns:
        Path: Absolute path to the cache base directory.
    """
    base = os.environ.get("WINDTRADER_CACHE_DIR")
    if base:
        return Path(base).expanduser().resolve()
    return Path.home() / ".cache" / "windtrader"


def _jar_cache_path(version: str) -> Path:
    """
    Return the expected local cache path for the given windtrader-java version.

    Args:
        version: windtrader-java version string (e.g. "0.1.1").

    Returns:
        Path: Path where the JAR should be stored in the cache.
    """
    return _cache_dir() / "jars" / f"windtrader-java-{version}.jar"


def _download(url: str, dest: Path) -> None:
    """
    Download a URL to the destination path atomically.

    The download is written to a temporary file first and then replaced into place.
    This helps avoid leaving partial/corrupt JARs in the cache if the process is interrupted.

    Args:
        url: The URL to download.
        dest: Destination path for the downloaded content.

    Raises:
        URLError / HTTPError: If the network request fails.
        OSError: If writing to disk fails.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "windtrader/0.1.0 (+https://github.com/Westfall-io/windtrader)"},
    )

    with urllib.request.urlopen(req) as r, open(tmp, "wb") as f:
        f.write(r.read())

    tmp.replace(dest)


def _candidate_urls(version: str) -> list[str]:
    """
    Build a prioritized list of candidate GitHub Release URLs for a given version.

    This wrapper expects the Java validator JAR to be published as an asset on GitHub Releases.
    Because tag/asset conventions can vary, we try a small fallback list.

    Candidates include:
    - Optional stable asset URL (env: WINDTRADER_JAVA_STABLE_ASSET)
    - Tag formatted as `v{version}` with asset named `windtrader-java-{version}.jar`
    - Tag formatted as `{version}` with the same asset name
    - `releases/latest/download` as a fallback (still using the versioned filename)

    Args:
        version: windtrader-java version string (e.g. "0.1.1").

    Returns:
        list[str]: Candidate URLs to try in order.
    """
    repo = os.environ.get("WINDTRADER_JAVA_REPO", DEFAULT_REPO)

    stable_asset = os.environ.get("WINDTRADER_JAVA_STABLE_ASSET", "").strip()

    urls: list[str] = []
    if stable_asset:
        urls.append(stable_asset)

    urls.append(
        f"https://github.com/{repo}/releases/download/v{version}/windtrader-java-{version}.jar"
    )
    urls.append(
        f"https://github.com/{repo}/releases/download/{version}/windtrader-java-{version}.jar"
    )
    urls.append(f"https://github.com/{repo}/releases/latest/download/windtrader-java-{version}.jar")

    return urls


def get_jar_path(version: str) -> Path:
    """
    Ensure the requested windtrader-java JAR is present locally and return its path.

    If the JAR is already present in the local cache and appears non-empty, it is reused.
    Otherwise, the function attempts to download the JAR from GitHub Release URLs and
    caches it.

    Args:
        version: windtrader-java version to fetch. If blank/None-like, DEFAULT_VERSION is used.

    Returns:
        Path: Local filesystem path to the cached JAR.

    Raises:
        RuntimeError: If the JAR could not be downloaded from any candidate URL.
    """
    version = (version or "").strip() or DEFAULT_VERSION
    dest = _jar_cache_path(version)

    if dest.exists() and dest.stat().st_size > 0:
        return dest

    last_err: Exception | None = None
    tried: list[str] = []

    for url in _candidate_urls(version):
        tried.append(url)
        try:
            _download(url, dest)
            if dest.exists() and dest.stat().st_size > 0:
                return dest
        except Exception as e:
            last_err = e

    msg = "Failed to download windtrader-java jar.\nTried:\n" + "\n".join(f"  - {u}" for u in tried)
    raise RuntimeError(msg) from last_err
