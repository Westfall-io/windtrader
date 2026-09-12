"""
Unit tests for `windtrader._jars`.

These tests never touch the network: every test either monkeypatches
``windtrader._jars._download`` or uses a local ``file://`` URL.
"""

from __future__ import annotations

import urllib.error
from pathlib import Path

import pytest

from windtrader import _jars

DEFAULT_REPO = "Westfall-io/windtrader-java"


@pytest.fixture(autouse=True)
def isolated_cache_env(monkeypatch, tmp_path):
    """Point the jar cache at a temp dir and clear jar-related env for every test."""
    monkeypatch.setenv("WINDTRADER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("WINDTRADER_JAVA_REPO", raising=False)
    monkeypatch.delenv("WINDTRADER_JAVA_STABLE_ASSET", raising=False)
    return tmp_path


def _recording_download(calls: list[str], payload: bytes = b"PK\x03\x04fake-jar"):
    """Build a fake `_download` that records URLs and writes `payload` to the destination."""

    def _download(url: str, dest: Path) -> None:
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)

    return _download


def _failing_download(calls: list[str], succeed_on: str | None = None):
    """Build a fake `_download` that fails for every URL except (optionally) `succeed_on`."""

    def _download(url: str, dest: Path) -> None:
        calls.append(url)
        if url == succeed_on:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"PK\x03\x04fake-jar")
            return
        raise urllib.error.URLError(f"boom: {url}")

    return _download


# ---------------------------------------------------------------------------
# _cache_dir / _jar_cache_path
# ---------------------------------------------------------------------------


def test_cache_dir_honors_env_override(monkeypatch, tmp_path):
    """WINDTRADER_CACHE_DIR wins over the default `~/.cache/windtrader` location."""
    monkeypatch.setenv("WINDTRADER_CACHE_DIR", str(tmp_path / "custom"))
    assert _jars._cache_dir() == (tmp_path / "custom").resolve()


def test_cache_dir_defaults_to_home_cache(monkeypatch, tmp_path):
    """With no env override the cache lives under `~/.cache/windtrader`."""
    monkeypatch.delenv("WINDTRADER_CACHE_DIR", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    assert _jars._cache_dir() == tmp_path / "home" / ".cache" / "windtrader"


def test_cache_dir_expands_user(monkeypatch, tmp_path):
    """A `~`-relative override is expanded rather than taken literally."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("WINDTRADER_CACHE_DIR", "~/wt")
    assert _jars._cache_dir() == (tmp_path / "home" / "wt").resolve()


def test_jar_cache_path_layout(monkeypatch, tmp_path):
    """Jars are cached as `<cache>/jars/windtrader-java-<version>.jar`."""
    monkeypatch.setenv("WINDTRADER_CACHE_DIR", str(tmp_path))
    assert (
        _jars._jar_cache_path("0.1.2") == tmp_path.resolve() / "jars" / "windtrader-java-0.1.2.jar"
    )


def test_jar_cache_path_is_version_specific(monkeypatch, tmp_path):
    """Different versions map to different cache files."""
    monkeypatch.setenv("WINDTRADER_CACHE_DIR", str(tmp_path))
    assert _jars._jar_cache_path("0.1.1") != _jars._jar_cache_path("0.1.2")


# ---------------------------------------------------------------------------
# _candidate_urls
# ---------------------------------------------------------------------------


def test_candidate_urls_default_order():
    """Without env overrides: `v<version>` tag, bare `<version>` tag, then `latest`."""
    assert _jars._candidate_urls("0.1.2") == [
        f"https://github.com/{DEFAULT_REPO}/releases/download/v0.1.2/windtrader-java-0.1.2.jar",
        f"https://github.com/{DEFAULT_REPO}/releases/download/0.1.2/windtrader-java-0.1.2.jar",
        f"https://github.com/{DEFAULT_REPO}/releases/latest/download/windtrader-java-0.1.2.jar",
    ]


def test_candidate_urls_stable_asset_is_first(monkeypatch):
    """WINDTRADER_JAVA_STABLE_ASSET is prepended as the first-choice download target."""
    monkeypatch.setenv("WINDTRADER_JAVA_STABLE_ASSET", "https://example.invalid/stable.jar")
    urls = _jars._candidate_urls("0.1.2")
    assert urls[0] == "https://example.invalid/stable.jar"
    assert len(urls) == 4
    assert urls[1:] == _candidate_urls_without_stable("0.1.2")


def _candidate_urls_without_stable(version: str) -> list[str]:
    """Return the three default release URLs for `version` (no stable-asset entry)."""
    base = f"https://github.com/{DEFAULT_REPO}/releases"
    asset = f"windtrader-java-{version}.jar"
    return [
        f"{base}/download/v{version}/{asset}",
        f"{base}/download/{version}/{asset}",
        f"{base}/latest/download/{asset}",
    ]


def test_candidate_urls_blank_stable_asset_is_ignored(monkeypatch):
    """A whitespace-only stable asset is stripped and contributes no candidate."""
    monkeypatch.setenv("WINDTRADER_JAVA_STABLE_ASSET", "   ")
    assert _jars._candidate_urls("0.1.2") == _candidate_urls_without_stable("0.1.2")


def test_candidate_urls_stable_asset_is_stripped(monkeypatch):
    """Surrounding whitespace is trimmed off the stable asset URL."""
    monkeypatch.setenv("WINDTRADER_JAVA_STABLE_ASSET", "  https://example.invalid/s.jar\n")
    assert _jars._candidate_urls("0.1.2")[0] == "https://example.invalid/s.jar"


def test_candidate_urls_honor_repo_override(monkeypatch):
    """WINDTRADER_JAVA_REPO replaces the default GitHub repo in every candidate."""
    monkeypatch.setenv("WINDTRADER_JAVA_REPO", "acme/forked-java")
    urls = _jars._candidate_urls("9.9.9")
    assert all(u.startswith("https://github.com/acme/forked-java/") for u in urls)
    assert all(u.endswith("windtrader-java-9.9.9.jar") for u in urls)


# ---------------------------------------------------------------------------
# _download
# ---------------------------------------------------------------------------


def test_download_writes_atomically_from_file_url(tmp_path):
    """`_download` fetches the URL, writes the destination, and leaves no `.tmp` behind."""
    src = tmp_path / "source.jar"
    src.write_bytes(b"PK\x03\x04payload")
    dest = tmp_path / "nested" / "out.jar"

    _jars._download(src.as_uri(), dest)

    assert dest.read_bytes() == b"PK\x03\x04payload"
    assert not (tmp_path / "nested" / "out.jar.tmp").exists()


def test_download_propagates_errors(tmp_path):
    """A failed fetch raises rather than leaving a bogus destination file."""
    dest = tmp_path / "out.jar"
    with pytest.raises(urllib.error.URLError):
        _jars._download((tmp_path / "missing.jar").as_uri(), dest)
    assert not dest.exists()


# ---------------------------------------------------------------------------
# get_jar_path
# ---------------------------------------------------------------------------


def test_get_jar_path_downloads_then_caches(monkeypatch):
    """The first call downloads; the second reuses the cached jar without re-downloading."""
    calls: list[str] = []
    monkeypatch.setattr(_jars, "_download", _recording_download(calls))

    first = _jars.get_jar_path("0.1.2")
    assert first.exists()
    assert len(calls) == 1

    second = _jars.get_jar_path("0.1.2")
    assert second == first
    assert len(calls) == 1, "cached jar must not be re-downloaded"


def test_get_jar_path_uses_precreated_jar_without_downloading(monkeypatch):
    """A jar already present in the cache short-circuits the download path entirely."""
    dest = _jars._jar_cache_path("0.1.2")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"PK\x03\x04already-here")

    def _boom(url: str, dest: Path) -> None:
        raise AssertionError(f"unexpected download attempt: {url}")

    monkeypatch.setattr(_jars, "_download", _boom)

    assert _jars.get_jar_path("0.1.2") == dest
    assert dest.read_bytes() == b"PK\x03\x04already-here"


def test_get_jar_path_refetches_empty_cached_jar(monkeypatch):
    """A zero-byte cache entry is treated as missing and re-downloaded."""
    dest = _jars._jar_cache_path("0.1.2")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"")

    calls: list[str] = []
    monkeypatch.setattr(_jars, "_download", _recording_download(calls))

    assert _jars.get_jar_path("0.1.2") == dest
    assert len(calls) == 1
    assert dest.stat().st_size > 0


def test_get_jar_path_defaults_blank_version(monkeypatch):
    """Blank/whitespace versions fall back to DEFAULT_VERSION."""
    calls: list[str] = []
    monkeypatch.setattr(_jars, "_download", _recording_download(calls))

    path = _jars.get_jar_path("   ")

    assert path.name == f"windtrader-java-{_jars.DEFAULT_VERSION}.jar"
    assert calls == _jars._candidate_urls(_jars.DEFAULT_VERSION)[:1]


def test_get_jar_path_falls_through_to_next_candidate(monkeypatch):
    """When the first candidate URL fails, the next one is tried."""
    candidates = _jars._candidate_urls("0.1.2")
    calls: list[str] = []
    monkeypatch.setattr(_jars, "_download", _failing_download(calls, succeed_on=candidates[1]))

    path = _jars.get_jar_path("0.1.2")

    assert path.exists()
    assert calls == candidates[:2], "must stop as soon as a candidate succeeds"


def test_get_jar_path_skips_candidate_that_wrote_empty_file(monkeypatch):
    """A 'successful' download that produced an empty file does not count as a hit."""
    candidates = _jars._candidate_urls("0.1.2")
    calls: list[str] = []

    def _download(url: str, dest: Path) -> None:
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"" if url != candidates[2] else b"PK\x03\x04real")

    monkeypatch.setattr(_jars, "_download", _download)

    path = _jars.get_jar_path("0.1.2")

    assert calls == candidates
    assert path.read_bytes() == b"PK\x03\x04real"


def test_get_jar_path_raises_runtime_error_listing_tried_urls(monkeypatch):
    """When every candidate fails, the RuntimeError names each URL that was attempted."""
    candidates = _jars._candidate_urls("0.1.2")
    calls: list[str] = []
    monkeypatch.setattr(_jars, "_download", _failing_download(calls))

    with pytest.raises(RuntimeError) as excinfo:
        _jars.get_jar_path("0.1.2")

    msg = str(excinfo.value)
    assert "Failed to download windtrader-java jar." in msg
    for url in candidates:
        assert url in msg
    assert calls == candidates
    assert isinstance(excinfo.value.__cause__, urllib.error.URLError)


def test_get_jar_path_error_includes_stable_asset(monkeypatch):
    """The stable-asset URL is reported in the failure message when configured."""
    monkeypatch.setenv("WINDTRADER_JAVA_STABLE_ASSET", "https://example.invalid/stable.jar")
    monkeypatch.setattr(_jars, "_download", _failing_download([]))

    with pytest.raises(RuntimeError, match="https://example.invalid/stable.jar"):
        _jars.get_jar_path("0.1.2")
