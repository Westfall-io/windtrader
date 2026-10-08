"""
Unit tests for `windtrader.cli`.

`windtrader.cli.validate` is monkeypatched throughout, so no JVM, jar or network is
required. The assertions pin the CLI contract: stdin in, verbatim streams out, jar
exit code forwarded.
"""

from __future__ import annotations

import io
import subprocess
import sys

import pytest

import windtrader
from windtrader import cli
from windtrader.client import DEFAULT_VERSION, CommandResult


def _result(exit_code: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    """Build a CommandResult standing in for one jar invocation."""
    return CommandResult(
        ok=exit_code == 0,
        version="0.1.2",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        jar_path="/fake/windtrader-java-0.1.2.jar",
        duration_s=0.01,
    )


@pytest.fixture
def fake_validate(monkeypatch):
    """
    Replace `cli.validate` with a recorder.

    `.calls` holds one (args, kwargs) tuple per call; set `.result` to control the
    ValidationResult that `main()` sees.
    """

    class Recorder:
        """Captures validate() calls made by the CLI and returns a canned result."""

        def __init__(self) -> None:
            self.calls: list[tuple[tuple, dict]] = []
            self.result = _result(0)

        def __call__(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return self.result

    recorder = Recorder()
    monkeypatch.setattr(cli, "validate", recorder)
    return recorder


@pytest.fixture
def stdin_text(monkeypatch):
    """Return a helper that installs `text` as the CLI's stdin."""

    def _set(text: str) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(text))

    return _set


@pytest.fixture
def fake_export(monkeypatch):
    """Replace `cli.client_export` with a recorder for export-subcommand tests."""

    class Recorder:
        """Captures export() calls made by the CLI and returns a canned result."""

        def __init__(self) -> None:
            self.calls: list[tuple[tuple, dict]] = []
            self.result = _result(0)

        def __call__(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return self.result

    recorder = Recorder()
    monkeypatch.setattr(cli, "client_export", recorder)
    return recorder


@pytest.fixture
def fake_echo(monkeypatch):
    """Replace `cli.client_echo` with a recorder for echo-subcommand tests."""

    class Recorder:
        """Captures echo() calls made by the CLI and returns a canned result."""

        def __init__(self) -> None:
            self.calls: list[tuple[tuple, dict]] = []
            self.result = _result(0)

        def __call__(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return self.result

    recorder = Recorder()
    monkeypatch.setattr(cli, "client_echo", recorder)
    return recorder


# ---------------------------------------------------------------------------
# stdin handling and argument forwarding
# ---------------------------------------------------------------------------


def test_reads_stdin_verbatim(fake_validate, stdin_text):
    """Everything on stdin, including trailing newlines, is passed to the validator."""
    stdin_text("part {\n  attribute mass;\n}\n")

    cli.main([])

    assert fake_validate.calls[0][0][0] == "part {\n  attribute mass;\n}\n"


def test_empty_stdin_is_still_validated(fake_validate, stdin_text):
    """Empty input is forwarded to the jar rather than short-circuited."""
    stdin_text("")

    assert cli.main([]) == 0
    assert fake_validate.calls[0][0][0] == ""


def test_default_java_version_and_timeout(fake_validate, stdin_text):
    """Defaults are the shared DEFAULT_VERSION and a 10 second timeout."""
    stdin_text("part def P;")

    cli.main([])

    kwargs = fake_validate.calls[0][1]
    assert kwargs["version"] == DEFAULT_VERSION
    assert kwargs["timeout_s"] == 10.0


def test_java_version_flag_is_forwarded(fake_validate, stdin_text):
    """`--java-version` selects the backend jar version."""
    stdin_text("part def P;")

    cli.main(["--java-version", "0.1.1"])

    assert fake_validate.calls[0][1]["version"] == "0.1.1"


def test_timeout_flag_is_forwarded_as_float(fake_validate, stdin_text):
    """`--timeout` is parsed as a float and forwarded."""
    stdin_text("part def P;")

    cli.main(["--timeout", "2.5"])

    assert fake_validate.calls[0][1]["timeout_s"] == 2.5


def test_invalid_timeout_flag_exits_with_usage_error(fake_validate, stdin_text):
    """A non-numeric timeout is an argparse usage error (exit 2), not a jar call."""
    stdin_text("part def P;")

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--timeout", "not-a-number"])

    assert excinfo.value.code == 2
    assert fake_validate.calls == []


# ---------------------------------------------------------------------------
# exit code forwarding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("exit_code", [0, 2, 3, 1, 42])
def test_forwards_jar_exit_code(fake_validate, stdin_text, exit_code):
    """`main()` returns exactly the exit code reported by the jar."""
    stdin_text("part def P;")
    fake_validate.result = _result(exit_code)

    assert cli.main([]) == exit_code


def test_exit_code_is_an_int(fake_validate, stdin_text):
    """The return value is a plain int suitable for `SystemExit`."""
    stdin_text("part def P;")
    fake_validate.result = _result(2)

    rc = cli.main([])

    assert isinstance(rc, int)
    assert rc == 2


# ---------------------------------------------------------------------------
# export subcommand
# ---------------------------------------------------------------------------


def test_export_subcommand_runs_export_on_stdin(fake_export, stdin_text):
    """`windtrader export` calls `client_export` with the stdin text."""
    stdin_text("part def P;")

    cli.main(["export"])

    assert len(fake_export.calls) == 1
    assert fake_export.calls[0][0][0] == "part def P;"


def test_export_subcommand_forwards_defaults(fake_export, stdin_text):
    """`export` uses the shared DEFAULT_VERSION and a 60s default timeout."""
    stdin_text("part def P;")

    cli.main(["export"])

    kwargs = fake_export.calls[0][1]
    assert kwargs["version"] == DEFAULT_VERSION
    assert kwargs["timeout_s"] == 60.0


def test_check_subcommand_uses_ten_second_default(fake_validate, stdin_text):
    """`check` (default) uses a 10s default timeout."""
    stdin_text("part def P;")

    cli.main([])

    assert fake_validate.calls[0][1]["timeout_s"] == 10.0


def test_export_subcommand_accepts_java_version_and_timeout(fake_export, stdin_text):
    """`export` honors `--java-version` and `--timeout`."""
    stdin_text("part def P;")

    cli.main(["export", "--java-version", "0.1.1", "--timeout", "5.0"])

    kwargs = fake_export.calls[0][1]
    assert kwargs["version"] == "0.1.1"
    assert kwargs["timeout_s"] == 5.0


def test_export_subcommand_forwards_exit_code(fake_export, stdin_text):
    """`windtrader export` returns the jar's exit code (0 valid, 2 invalid, 3 runtime)."""
    for code in (0, 2, 3):
        stdin_text("part def P;")
        fake_export.result = _result(code)
        assert cli.main(["export"]) == code


def test_export_subcommand_forwards_json_stdout(fake_export, stdin_text, capsys):
    """JSON from a successful export is written to stdout verbatim."""
    stdin_text("part def P;")
    fake_export.result = _result(0, stdout='[{"@id": "x", "@type": "PartUsage"}]')

    cli.main(["export"])

    captured = capsys.readouterr()
    assert captured.out == '[{"@id": "x", "@type": "PartUsage"}]\n'


def test_export_subcommand_forwards_stderr(fake_export, stdin_text, capsys):
    """Export diagnostics (e.g. parse errors) land on stderr verbatim."""
    stdin_text("not sysml")
    fake_export.result = _result(2, stdout="", stderr="error: line=1 offset=3 near=not")

    cli.main(["export"])

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: line=1 offset=3 near=not\n"


# ---------------------------------------------------------------------------
# echo subcommand
# ---------------------------------------------------------------------------


def test_echo_subcommand_runs_echo_on_stdin(fake_echo, stdin_text):
    """`windtrader echo` calls `client_echo` with the stdin text."""
    stdin_text("part def P;")

    cli.main(["echo"])

    assert len(fake_echo.calls) == 1
    assert fake_echo.calls[0][0][0] == "part def P;"


def test_echo_subcommand_forwards_defaults(fake_echo, stdin_text):
    """`echo` uses the shared DEFAULT_VERSION and a 10s default timeout."""
    stdin_text("part def P;")

    cli.main(["echo"])

    kwargs = fake_echo.calls[0][1]
    assert kwargs["version"] == DEFAULT_VERSION
    assert kwargs["timeout_s"] == 10.0


def test_echo_subcommand_forwards_exit_code(fake_echo, stdin_text):
    """`windtrader echo` returns the jar's exit code."""
    stdin_text("part def P;")
    fake_echo.result = _result(2)

    assert cli.main(["echo"]) == 2


# ---------------------------------------------------------------------------
# timeout handling
# ---------------------------------------------------------------------------


def test_timeout_returns_runtime_error_exit_3(monkeypatch, stdin_text, capsys):
    """A subprocess timeout is caught and surfaced as exit 3, not a traceback."""
    stdin_text("part def P;")

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["java"], timeout=30.0)

    monkeypatch.setattr(cli, "client_export", _raise_timeout)

    rc = cli.main(["export"])

    assert rc == 3
    assert "timeout" in capsys.readouterr().err.lower()


# ---------------------------------------------------------------------------
# stream passthrough
# ---------------------------------------------------------------------------


def test_stdout_and_stderr_are_forwarded_verbatim(fake_validate, stdin_text, capsys):
    """Jar stdout goes to stdout and jar stderr to stderr, unchanged."""
    stdin_text("part def P;")
    fake_validate.result = _result(
        2, stdout="part def P;\n", stderr="error: line=1 offset=14 near=mass\n"
    )

    cli.main([])

    captured = capsys.readouterr()
    assert captured.out == "part def P;\n"
    assert captured.err == "error: line=1 offset=14 near=mass\n"


def test_missing_trailing_newline_is_added(fake_validate, stdin_text, capsys):
    """Output without a trailing newline gets exactly one appended, per stream."""
    stdin_text("part def P;")
    fake_validate.result = _result(2, stdout="no newline", stderr="error: nope")

    cli.main([])

    captured = capsys.readouterr()
    assert captured.out == "no newline\n"
    assert captured.err == "error: nope\n"


def test_existing_trailing_newline_is_not_doubled(fake_validate, stdin_text, capsys):
    """A stream that already ends in a newline is not padded further."""
    stdin_text("part def P;")
    fake_validate.result = _result(0, stdout="already\n", stderr="warn\n")

    cli.main([])

    captured = capsys.readouterr()
    assert captured.out == "already\n"
    assert captured.err == "warn\n"


def test_empty_streams_produce_no_output(fake_validate, stdin_text, capsys):
    """Nothing is written when the jar produced no output at all."""
    stdin_text("part def P;")
    fake_validate.result = _result(0, stdout="", stderr="")

    cli.main([])

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_stdout_only_leaves_stderr_clean(fake_validate, stdin_text, capsys):
    """Stream forwarding is independent: stdout content does not leak into stderr."""
    stdin_text("part def P;")
    fake_validate.result = _result(0, stdout="part def P;")

    cli.main([])

    captured = capsys.readouterr()
    assert captured.out == "part def P;\n"
    assert captured.err == ""


# ---------------------------------------------------------------------------
# --version / --help
# ---------------------------------------------------------------------------


def test_version_flag_prints_package_version(capsys):
    """`--version` prints the Python package version and exits 0."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])

    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"windtrader {windtrader.__version__}"


def test_version_flag_does_not_read_stdin(fake_validate):
    """`--version` short-circuits before stdin is consumed or the jar is run."""
    with pytest.raises(SystemExit):
        cli.main(["--version"])

    assert fake_validate.calls == []


def test_help_flag_exits_zero_and_documents_flags(capsys):
    """`--help` exits 0 and mentions the backend flags."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])

    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "--java-version" in out
    assert "--timeout" in out
