# Windtrader

**Windtrader** is a lightweight Python wrapper around **windtrader-java**, providing fast, parse-only validation for **SysML v2** models.

The Python package does **not** reimplement the language. Instead, it delegates validation to a versioned Java JAR published via GitHub Releases, downloads it on demand, and caches it locally.

---

## Features

* ✅ Parse-only SysML v2 validation
* 🚀 Thin Python API over a stable Java engine
* 📦 Automatic JAR download + local caching
* 🔁 Version-pinned Java backend per invocation
* 🧪 Designed for CI, linters, and pre-commit checks

---

## Installation

```bash
pip install windtrader
```

For development:

```bash
pip install -e ".[dev]"
```

---

## Command-Line Usage

Windtrader reads SysML text from **stdin** and exits with the same status code as the Java validator.

```bash
echo "part { attribute mass; }" | windtrader
```

### Options

```text
--version   windtrader-java version to use (default: 0.1.1)
--timeout   timeout in seconds (default: 10.0)
```

Example:

```bash
echo "part { attrib mass; }" | windtrader --version 0.1.1
```

Exit codes:

| Code | Meaning              |
| ---: | -------------------- |
|    0 | Valid SysML          |
|    2 | Invalid syntax       |
|   3+ | Runtime / tool error |

---

## Python API

```python
from windtrader.validator import WindtraderValidator

v = WindtraderValidator(version="0.1.1")
res = v.validate_text("part { attribute mass; }")

if res.ok:
    print("Valid SysML")
else:
    print("Invalid SysML")
    print(res.stderr)
```

### `ValidationResult`

Returned from all validation calls:

```python
ValidationResult(
    ok: bool,
    version: str,
    exit_code: int,
    stdout: str,
    stderr: str,
    jar_path: str,
    duration_s: float,
)
```

Convenience properties:

* `is_invalid_syntax`
* `is_runtime_error`

---

## JAR Download & Caching

Downloaded JARs are cached locally:

```text
~/.cache/windtrader/jars/
```

You may override this location:

```bash
export WINDTRADER_CACHE_DIR=/path/to/cache
```

To force a fresh download:

```bash
rm -rf ~/.cache/windtrader/jars
```

---

## Environment Variables

| Variable                       | Purpose                                |
| ------------------------------ | -------------------------------------- |
| `WINDTRADER_JAVA_REPO`         | Override GitHub repo for JAR downloads |
| `WINDTRADER_CACHE_DIR`         | Override cache directory               |
| `WINDTRADER_JAVA_STABLE_ASSET` | Optional fixed asset URL               |

---

## Development

```bash
pytest
ruff check src/
```

The Python package intentionally **does not** modify or manage Maven, Java versions, or semantic-release state. All Java versioning is handled by `windtrader-java` releases.

---

## License

MIT License. See `LICENSE` for details.

---

## Project Status

This project is intentionally minimal and strict in scope. It exists to provide:

* Deterministic SysML parsing
* Clear failure modes
* Stable CI integration

Feature requests that require semantic interpretation should be implemented upstream in **windtrader-java**.
