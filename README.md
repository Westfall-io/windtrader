# windtrader (Python wrapper)

This repository provides a small Python wrapper around the `windtrader-java` validator.
The wrapper locates/downloads a pinned Java validator JAR, invokes it as a subprocess,
and exposes a concise API and CLI for validating SysML v2 textual inputs.

## Purpose

- Make the `windtrader-java` validator easy to use from Python and CI jobs.
- Cache downloaded Java validator JARs to minimize repeated network downloads.
- Provide a stable `ValidationResult` typed API for callers and tests.

## Key modules

- `src/windtrader/_jars.py` — JAR resolution and download helpers.
  - Resolves a local cache directory (default `~/.cache/windtrader`).
  - Builds candidate GitHub Release URLs and attempts to download the JAR.
  - Writes downloads atomically to avoid leaving partial files.
  - Environment variables:
    - `WINDTRADER_CACHE_DIR` — override cache root.
    - `WINDTRADER_JAVA_REPO` — override GitHub repo used for releases.
    - `WINDTRADER_JAVA_STABLE_ASSET` — optional exact download URL (first choice).

- `src/windtrader/_types.py` — small dataclasses used by the wrapper.
  - `ValidationError` — single parse diagnostic.
  - `ValidationResult` — summary of a validation run (stdout, stderr, exit code).
  - `CrossVersionResult` — container used when comparing results across versions.

- `src/windtrader/validator.py` — Python surface for invoking the Java validator.
  - `WindtraderValidator` class resolves the jar and runs `java -jar <jar> check` and
    `echo` with a bounded timeout, returning a `ValidationResult`.
  - `validate()` convenience function wraps a one-shot invocation.
  - `validate_across_versions()` runs the same text against multiple versions.

- `src/windtrader/cli.py` — lightweight CLI wrapper.
  - Reads SysML text from stdin, calls `validate()`, forwards stdout/stderr,
    and exits with the same exit code as the Java tool.

## Usage examples

Validate a file from the shell (requires `java` on PATH):

```bash
cat model.sysml | python -m windtrader.cli --java-version 0.1.1
```

Use the Python API:

```python
from windtrader import validate

res = validate("my sysml text here", version="0.1.1", timeout_s=10.0)
print(res.exit_code, res.stdout, res.stderr)
```

Validate across versions:

```python
from windtrader import validate_across_versions

versions = ["0.1.1", "0.1.0"]
results = validate_across_versions("...text...", versions)
for r in results:
    print(r.version, r.exit_code)
```

## Behavior & exit codes

The wrapper preserves exit conventions from `windtrader-java`:
- `0` => valid syntax
- `2` => invalid syntax (parse error)
- `3` => runtime / tool error

The CLI forwards stdout/stderr and returns the Java process exit code.

## Notes on caching and CI

- JARs are cached under `~/.cache/windtrader/jars` by default. In CI, set
  `WINDTRADER_CACHE_DIR` to a persistent cache directory to avoid repeated downloads.
- If you provide `WINDTRADER_JAVA_STABLE_ASSET`, that URL is tried first.

## Testing

Run the test suite with `pytest` from repo root (requires test dependencies):

```bash
python -m pytest -q
```

## Requirements

- Java runtime (`java`) must be available on `PATH` to run the downloaded JAR.
- Network access is required the first time a requested JAR version is fetched.

## Contributing

- Keep module-level documentation up to date when changing public behavior.
- Prefer immutable dataclasses in `_types.py` for stable test assertions.

---

This `README_GIT.md` is intended as a quick developer-oriented summary of what the
code does and how to use it from the command line and Python code. For broader
project details, see `README.md`.
