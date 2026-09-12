"""
Unit tests for `windtrader.validator`.

No JVM and no network: `subprocess.run` and `get_jar_path` are both monkeypatched,
so these tests run anywhere and assert the exact contract the wrapper has with the
`windtrader-java` CLI.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import windtrader
from windtrader import validator as validator_mod
from windtrader.validator import (
    ValidationResult,
    WindtraderValidator,
    validate,
    validate_across_versions,
)

FAKE_JAR = Path("/fake/cache/jars/windtrader-java-0.1.2.jar")


def _result(exit_code: int = 0, **overrides) -> ValidationResult:
    """Build a ValidationResult with sensible defaults for property-level assertions."""
    fields = {
        "ok": exit_code == 0,
        "version": "0.1.2",
        "exit_code": exit_code,
        "stdout": "",
        "stderr": "",
        "jar_path": str(FAKE_JAR),
        "duration_s": 0.0,
    }
    fields.update(overrides)
    return ValidationResult(**fields)


class FakeCompletedProcess:
    """Stand-in for `subprocess.CompletedProcess` with only the attributes we read."""

    def __init__(self, returncode: int, stdout: str | None, stderr: str | None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def fake_run(monkeypatch):
    """
    Replace `subprocess.run` and `get_jar_path` inside the validator module.

    Returns a recorder object whose `.calls` holds one (args, kwargs) tuple per
    invocation, and whose `.returncode` / `.stdout` / `.stderr` configure the reply.
    """

    class Recorder:
        """Captures subprocess invocations and serves a canned CompletedProcess."""

        def __init__(self) -> None:
            self.calls: list[tuple[tuple, dict]] = []
            self.returncode = 0
            self.stdout: str | None = ""
            self.stderr: str | None = ""

        def __call__(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return FakeCompletedProcess(self.returncode, self.stdout, self.stderr)

        @property
        def argv(self) -> list[str]:
            """The argv list of the most recent subprocess call."""
            return self.calls[-1][0][0]

        @property
        def kwargs(self) -> dict:
            """The keyword arguments of the most recent subprocess call."""
            return self.calls[-1][1]

    recorder = Recorder()
    monkeypatch.setattr(validator_mod.subprocess, "run", recorder)
    monkeypatch.setattr(validator_mod, "get_jar_path", lambda version: FAKE_JAR)
    return recorder


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


def test_valid_result_flags():
    """Exit 0 is a clean pass: neither invalid syntax nor a runtime error."""
    res = _result(0)
    assert res.ok is True
    assert res.is_invalid_syntax is False
    assert res.is_runtime_error is False


def test_parse_error_result_flags():
    """Exit 2 means invalid syntax, which is explicitly not a runtime error."""
    res = _result(2)
    assert res.ok is False
    assert res.is_invalid_syntax is True
    assert res.is_runtime_error is False


@pytest.mark.parametrize("exit_code", [1, 3, 127, -9])
def test_runtime_error_result_flags(exit_code):
    """Any exit code outside (0, 2) is surfaced as a runtime/tool error."""
    res = _result(exit_code)
    assert res.ok is False
    assert res.is_invalid_syntax is False
    assert res.is_runtime_error is True


def test_validation_result_is_frozen():
    """ValidationResult is immutable so callers cannot mutate reported outcomes."""
    res = _result(0)
    with pytest.raises(Exception):  # noqa: B017 - dataclasses raise FrozenInstanceError
        res.ok = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# WindtraderValidator.validate_text / echo
# ---------------------------------------------------------------------------


def test_validate_text_builds_exact_check_argv(fake_run):
    """`check` is invoked as exactly ["java", "-jar", <jar>, "check"]."""
    WindtraderValidator().validate_text("part { attribute mass; }")

    assert fake_run.argv == ["java", "-jar", str(FAKE_JAR), "check"]


def test_echo_builds_exact_echo_argv(fake_run):
    """`echo` is invoked as exactly ["java", "-jar", <jar>, "echo"]."""
    WindtraderValidator().echo("part { attribute mass; }")

    assert fake_run.argv == ["java", "-jar", str(FAKE_JAR), "echo"]


def test_validate_text_passes_input_as_text(fake_run):
    """The SysML source is piped to the jar via stdin in text mode with output captured."""
    WindtraderValidator().validate_text("part def P;")

    kwargs = fake_run.kwargs
    assert kwargs["input"] == "part def P;"
    assert kwargs["text"] is True
    assert kwargs["capture_output"] is True
    assert kwargs["check"] is False


def test_validate_text_passes_timeout_through(fake_run):
    """The caller's timeout reaches `subprocess.run` unchanged."""
    WindtraderValidator().validate_text("part def P;", timeout_s=2.5)
    assert fake_run.kwargs["timeout"] == 2.5


def test_echo_passes_timeout_through(fake_run):
    """`echo` honors its own timeout argument."""
    WindtraderValidator().echo("part def P;", timeout_s=7.0)
    assert fake_run.kwargs["timeout"] == 7.0


def test_default_timeout_is_ten_seconds(fake_run):
    """The documented default subprocess timeout is 10 seconds."""
    WindtraderValidator().validate_text("part def P;")
    assert fake_run.kwargs["timeout"] == 10.0


def test_validate_text_surfaces_exit_code_and_streams(fake_run):
    """Exit code, stdout and stderr from the jar are surfaced verbatim."""
    fake_run.returncode = 2
    fake_run.stdout = "some output"
    fake_run.stderr = "error: line=1 offset=14 near=mass\n"

    res = WindtraderValidator().validate_text("part { attrib mass; }")

    assert res.ok is False
    assert res.exit_code == 2
    assert res.is_invalid_syntax is True
    assert res.stdout == "some output"
    assert res.stderr == "error: line=1 offset=14 near=mass\n"


def test_validate_text_coerces_none_streams_to_empty_strings(fake_run):
    """`None` streams become empty strings so callers never see `None`."""
    fake_run.stdout = None
    fake_run.stderr = None

    res = WindtraderValidator().validate_text("part def P;")

    assert res.stdout == ""
    assert res.stderr == ""


def test_result_metadata_reports_version_jar_and_duration(fake_run):
    """The result records the requested version, the resolved jar path and a duration."""
    res = WindtraderValidator(version="9.9.9").validate_text("part def P;")

    assert res.version == "9.9.9"
    assert res.jar_path == str(FAKE_JAR)
    assert res.duration_s >= 0.0


def test_validator_resolves_jar_for_its_own_version(monkeypatch, fake_run):
    """The configured version is the one handed to `get_jar_path`."""
    seen: list[str] = []

    def _get_jar_path(version: str) -> Path:
        """Record the requested version and return the fake jar path."""
        seen.append(version)
        return FAKE_JAR

    monkeypatch.setattr(validator_mod, "get_jar_path", _get_jar_path)

    WindtraderValidator(version="0.1.1").validate_text("part def P;")

    assert seen == ["0.1.1"]


def test_default_version_matches_module_constant(fake_run):
    """A default-constructed validator uses `validator.DEFAULT_VERSION`."""
    assert WindtraderValidator().version == validator_mod.DEFAULT_VERSION
    assert validator_mod.DEFAULT_VERSION == "0.1.2"


def test_timeout_expired_propagates(monkeypatch):
    """A subprocess timeout is raised to the caller rather than swallowed."""
    monkeypatch.setattr(validator_mod, "get_jar_path", lambda version: FAKE_JAR)

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 0.0))

    monkeypatch.setattr(validator_mod.subprocess, "run", _timeout)

    with pytest.raises(subprocess.TimeoutExpired):
        WindtraderValidator().validate_text("part def P;", timeout_s=0.01)


# ---------------------------------------------------------------------------
# validate() alias and module-level helpers
# ---------------------------------------------------------------------------


def test_validate_method_is_alias_for_validate_text(fake_run):
    """`WindtraderValidator.validate` delegates to `validate_text`, timeout included."""
    v = WindtraderValidator()
    via_alias = v.validate("part def P;", timeout_s=3.0)
    alias_call = fake_run.calls[-1]

    via_direct = v.validate_text("part def P;", timeout_s=3.0)
    direct_call = fake_run.calls[-1]

    assert alias_call[0] == direct_call[0]
    assert alias_call[1] == direct_call[1]
    assert via_alias.exit_code == via_direct.exit_code


def test_module_level_validate_uses_requested_version(fake_run):
    """The module-level `validate()` threads version and timeout to the subprocess call."""
    res = validate("part def P;", version="0.1.1", timeout_s=4.0)

    assert res.version == "0.1.1"
    assert fake_run.argv == ["java", "-jar", str(FAKE_JAR), "check"]
    assert fake_run.kwargs["timeout"] == 4.0


def test_validate_across_versions_preserves_order(fake_run):
    """One result per version, in the same order as the requested sequence."""
    versions = ["0.1.0", "0.1.1", "0.1.2"]

    results = validate_across_versions("part def P;", versions)

    assert [r.version for r in results] == versions
    assert len(fake_run.calls) == 3


def test_validate_across_versions_with_empty_sequence(fake_run):
    """An empty version list runs nothing and returns an empty list."""
    assert validate_across_versions("part def P;", []) == []
    assert fake_run.calls == []


def test_validate_across_versions_passes_timeout(fake_run):
    """Each per-version invocation uses the supplied timeout."""
    validate_across_versions("part def P;", ["0.1.1", "0.1.2"], timeout_s=1.5)

    assert [call[1]["timeout"] for call in fake_run.calls] == [1.5, 1.5]


# ---------------------------------------------------------------------------
# Package surface
# ---------------------------------------------------------------------------


def test_package_exports_public_api():
    """`windtrader` re-exports the documented public API."""
    assert set(windtrader.__all__) == {
        "ValidationResult",
        "WindtraderValidator",
        "validate",
        "validate_across_versions",
    }
    for name in windtrader.__all__:
        assert getattr(windtrader, name) is getattr(validator_mod, name)


def test_package_version_matches_validator_default():
    """The package version and the default java backend version stay in lockstep."""
    assert windtrader.__version__ == "0.1.2"
    assert windtrader.__version__ == validator_mod.DEFAULT_VERSION
