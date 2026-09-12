"""
Integration tests that run the REAL `windtrader-java` validator jar.

Every test in this module is marked `jar`. They require a Java runtime on PATH
(`java_min=21` per the jar's own `versions` output) and the pinned jar, which is
downloaded on demand into `WINDTRADER_CACHE_DIR` (or a temp dir when unset).

If java is missing the whole module skips with an explicit message -- it never
silently passes.

The corpus below is pinned to the observed behavior of the real jar:
exit 0 = valid, exit 2 = parse error, exit 3 = runtime/tool error.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys

import pytest

from windtrader import WindtraderValidator, cli, validate, validate_across_versions
from windtrader._jars import DEFAULT_VERSION, get_jar_path

pytestmark = pytest.mark.jar

# Generous enough to absorb JVM startup on a cold CI runner; still bounded.
TIMEOUT_S = 60.0

VALID_SOURCES = [
    pytest.param("part { attribute mass; }", id="part-with-attribute"),
    pytest.param("part def P { attribute m : ScalarValues::Real; }", id="typed-attribute"),
    pytest.param("part def P; part p : P;", id="def-and-usage"),
    pytest.param("/* a comment */ part { attribute mass; }", id="block-comment"),
    pytest.param("part {\n  attribute mass;\n  attribute vol;\n}", id="multiline"),
    pytest.param("", id="empty-input"),
]

INVALID_SOURCES = [
    pytest.param("part { attrib mass; }", id="misspelled-keyword"),
    pytest.param("requirement Req1 { doc /** heading **/; }", id="doc-comment-in-requirement"),
    pytest.param("part { @@@ ; }", id="illegal-symbols"),
    pytest.param("part { attribute méss; }", id="non-ascii-identifier"),
]

DIAGNOSTIC_RE = re.compile(r"^error: line=(\d+) offset=(\d+) near=", re.MULTILINE)


@pytest.fixture(scope="session")
def jar_path(tmp_path_factory):
    """
    Resolve the real windtrader-java jar, skipping the module if java is unavailable.

    Honors `WINDTRADER_CACHE_DIR` when the environment already sets it (CI pre-warms
    the cache); otherwise a session temp dir is used and the jar is downloaded once.
    """
    if shutil.which("java") is None:
        pytest.skip("java not on PATH: windtrader-java integration tests need a Java 21+ runtime")

    with pytest.MonkeyPatch.context() as mp:
        if not os.environ.get("WINDTRADER_CACHE_DIR"):
            mp.setenv("WINDTRADER_CACHE_DIR", str(tmp_path_factory.mktemp("windtrader-cache")))

        path = get_jar_path(DEFAULT_VERSION)
        assert path.exists() and path.stat().st_size > 0, f"jar missing or empty: {path}"

        # Keep the cache env in place for the whole session: the validator re-resolves
        # the jar path on every invocation.
        yield path


@pytest.fixture(scope="session")
def validator(jar_path):
    """A WindtraderValidator bound to the default (pinned) windtrader-java version."""
    return WindtraderValidator()


# ---------------------------------------------------------------------------
# check: valid corpus
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source", VALID_SOURCES)
def test_valid_source_exits_zero(validator, source):
    """Every source in the valid corpus parses cleanly (exit 0, no diagnostics)."""
    res = validator.validate_text(source, timeout_s=TIMEOUT_S)

    assert res.exit_code == 0, f"unexpected exit {res.exit_code}; stderr={res.stderr!r}"
    assert res.ok is True
    assert res.is_invalid_syntax is False
    assert res.is_runtime_error is False
    assert "error:" not in res.stderr


def test_valid_result_reports_jar_metadata(validator, jar_path):
    """A real run records the jar it used, the version, and a positive duration."""
    res = validator.validate_text("part { attribute mass; }", timeout_s=TIMEOUT_S)

    assert res.jar_path == str(jar_path)
    assert res.version == DEFAULT_VERSION
    assert res.duration_s > 0.0


# ---------------------------------------------------------------------------
# check: invalid corpus
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source", INVALID_SOURCES)
def test_invalid_source_exits_two(validator, source):
    """Every source in the invalid corpus is a parse error (exit 2), not a tool crash."""
    res = validator.validate_text(source, timeout_s=TIMEOUT_S)

    assert res.exit_code == 2, f"unexpected exit {res.exit_code}; stderr={res.stderr!r}"
    assert res.ok is False
    assert res.is_invalid_syntax is True
    assert res.is_runtime_error is False
    assert "error:" in res.stderr


@pytest.mark.parametrize("source", INVALID_SOURCES)
def test_invalid_source_emits_located_diagnostic(validator, source):
    """Parse errors report `error: line=N offset=N near=...` with 1-based line numbers."""
    res = validator.validate_text(source, timeout_s=TIMEOUT_S)

    assert res.stderr.startswith("error:")
    matches = DIAGNOSTIC_RE.findall(res.stderr)
    assert matches, f"no located diagnostic in stderr={res.stderr!r}"
    line, offset = matches[0]
    assert int(line) == 1
    assert int(offset) >= 0


def test_misspelled_keyword_diagnostic_is_exact(validator):
    """The canonical parse error pins line, offset and the offending token."""
    res = validator.validate_text("part { attrib mass; }", timeout_s=TIMEOUT_S)

    assert res.exit_code == 2
    assert res.stderr.splitlines()[0] == "error: line=1 offset=14 near=mass"


def test_parse_error_leaves_stdout_empty(validator):
    """Diagnostics go to stderr only; stdout stays clean on a parse failure."""
    res = validator.validate_text("part { attrib mass; }", timeout_s=TIMEOUT_S)

    assert res.stdout == ""


# ---------------------------------------------------------------------------
# echo: parse -> canonicalize -> emit -> re-parse round trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source", VALID_SOURCES)
def test_echo_round_trips_valid_source(validator, source):
    """`echo` re-emits valid input byte-for-byte on stdout and exits 0."""
    res = validator.echo(source, timeout_s=TIMEOUT_S)

    assert res.exit_code == 0, f"unexpected exit {res.exit_code}; stderr={res.stderr!r}"
    assert res.ok is True
    assert res.stdout == source


@pytest.mark.parametrize("source", VALID_SOURCES)
def test_echoed_output_reparses_cleanly(validator, source):
    """The emitted text is itself valid SysML: parse -> emit -> re-parse stays exit 0."""
    emitted = validator.echo(source, timeout_s=TIMEOUT_S).stdout

    reparsed = validator.validate_text(emitted, timeout_s=TIMEOUT_S)

    assert reparsed.exit_code == 0
    assert reparsed.ok is True


@pytest.mark.parametrize("source", INVALID_SOURCES)
def test_echo_rejects_invalid_source(validator, source):
    """`echo` refuses to emit unparseable input and exits 2 like `check`."""
    res = validator.echo(source, timeout_s=TIMEOUT_S)

    assert res.exit_code == 2, f"unexpected exit {res.exit_code}; stderr={res.stderr!r}"
    assert res.is_invalid_syntax is True
    assert "error:" in res.stderr


# ---------------------------------------------------------------------------
# versions subcommand
# ---------------------------------------------------------------------------


def test_versions_subcommand_reports_tool_identity(jar_path):
    """`java -jar <jar> versions` self-describes the tool, mode and java floor."""
    proc = subprocess.run(
        ["java", "-jar", str(jar_path), "versions"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
        check=False,
    )

    assert proc.returncode == 0, f"stderr={proc.stderr!r}"
    assert "name=windtrader-java" in proc.stdout
    assert "mode=validator" in proc.stdout
    assert "validation=parse-only" in proc.stdout
    assert "java_min=21" in proc.stdout
    # Deliberately not asserting the exact sysml_version: the pin bumps over time.
    assert "sysml_version=" in proc.stdout


# ---------------------------------------------------------------------------
# public API against the real jar
# ---------------------------------------------------------------------------


def test_module_level_validate_against_real_jar(jar_path):
    """The one-call `validate()` helper works end to end without a validator instance."""
    assert validate("part def P; part p : P;", timeout_s=TIMEOUT_S).exit_code == 0
    assert validate("part { attrib mass; }", timeout_s=TIMEOUT_S).exit_code == 2


def test_validate_alias_matches_validate_text(validator):
    """The `validate` alias produces the same verdict as `validate_text`."""
    source = "part { attrib mass; }"

    assert validator.validate(source, timeout_s=TIMEOUT_S).exit_code == (
        validator.validate_text(source, timeout_s=TIMEOUT_S).exit_code
    )


def test_validate_across_versions_against_real_jar(jar_path):
    """Cross-version validation returns one real result per requested version, in order."""
    results = validate_across_versions(
        "part { attribute mass; }", [DEFAULT_VERSION], timeout_s=TIMEOUT_S
    )

    assert [r.version for r in results] == [DEFAULT_VERSION]
    assert results[0].exit_code == 0
    assert results[0].jar_path == str(jar_path)


# ---------------------------------------------------------------------------
# CLI against the real jar
# ---------------------------------------------------------------------------


def test_cli_forwards_real_exit_code_and_diagnostics(jar_path, monkeypatch, capsys):
    """`cli.main()` on invalid input exits 2 and relays the jar's diagnostic on stderr."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("part { attrib mass; }"))

    rc = cli.main(["--timeout", str(TIMEOUT_S)])

    captured = capsys.readouterr()
    assert rc == 2
    assert captured.err.startswith("error: line=1 offset=14 near=mass")


def test_cli_exits_zero_on_valid_input(jar_path, monkeypatch, capsys):
    """`cli.main()` on valid input exits 0 with no diagnostics."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("part { attribute mass; }"))

    rc = cli.main(["--timeout", str(TIMEOUT_S)])

    assert rc == 0
    assert "error:" not in capsys.readouterr().err
