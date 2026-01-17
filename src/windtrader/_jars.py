from __future__ import annotations

from pathlib import Path
import os
import urllib.request


DEFAULT_REPO = "Westfall-io/windtrader-java"
DEFAULT_VERSION = "0.1.1"  # <-- bump this


def _cache_dir() -> Path:
    # Simple, no extra deps. User can override.
    base = os.environ.get("WINDTRADER_CACHE_DIR")
    if base:
        return Path(base).expanduser().resolve()
    return Path.home() / ".cache" / "windtrader"


def _jar_cache_path(version: str) -> Path:
    return _cache_dir() / "jars" / f"windtrader-java-{version}.jar"


def _download(url: str, dest: Path) -> None:
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
    Your semantic-release GitHub asset is uploaded from: target/*.jar
    Common outcomes are:
      - tag: v0.1.0 asset: windtrader-java-0.1.0.jar
    But depending on your release config, tags/assets can vary.
    We try a small fallback set.
    """
    repo = os.environ.get("WINDTRADER_JAVA_REPO", DEFAULT_REPO)

    # If you ever decide to publish a stable asset name, add it here as first choice.
    # Example stable asset:
    #   https://github.com/<repo>/releases/latest/download/windtrader-java.jar
    stable_asset = os.environ.get("WINDTRADER_JAVA_STABLE_ASSET", "").strip()
    urls: list[str] = []
    if stable_asset:
        urls.append(stable_asset)

    # Typical semantic-release tag pattern with 'v'
    urls.append(
        f"https://github.com/{repo}/releases/download/v{version}/windtrader-java-{version}.jar"
    )
    # Fallback if tag has no 'v'
    urls.append(
        f"https://github.com/{repo}/releases/download/{version}/windtrader-java-{version}.jar"
    )
    # Fallback: latest/download with versioned filename (works if GitHub exposes that asset)
    urls.append(f"https://github.com/{repo}/releases/latest/download/windtrader-java-{version}.jar")

    return urls


def get_jar_path(version: str) -> Path:
    """
    Download+cache jar for requested version. Returns local filesystem path.

    Raises RuntimeError with the attempted URLs if download fails.
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
