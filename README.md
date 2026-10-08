# windtrader

**windtrader** is a lightweight Python wrapper around the `windtrader-java` SysML v2 validator.
It provides a simple, scriptable way to validate SysML v2 textual syntax from Python while
delegating all grammar authority to the official Java-based validator.

This project is intentionally *parse-only*: it validates syntax, reports diagnostics, and
(optionally) echoes parsed output, but does **not** perform semantic resolution or model linking.

---

## Status

![CI](https://github.com/Westfall-io/windtrader/actions/workflows/ci.yml/badge.svg)
![Coverage](https://codecov.io/gh/Westfall-io/windtrader/branch/main/graph/badge.svg)
![Docstrings](https://img.shields.io/badge/docstrings-interrogate-success)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/github/license/Westfall-io/windtrader)

---

## Key Features

- ✅ Validates SysML v2 textual syntax using a pinned Java validator
- 🧩 Thin, explicit Python API (no hidden model interpretation)
- 📦 Automatic download and caching of the validator JAR
- 🧪 Designed for CI, generators, and downstream tooling
- 🔐 Stable exit-code contract from Java → Python

---

## Installation

```bash
pip install windtrader
```

Or for development:

```bash
pip install -e ".[dev]"
```

Java **must** be available on your system (CI uses Temurin JDK).

---

## Command-Line Usage

```bash
echo "part { attribute mass; }" | windtrader           # validate (default: check)
echo "part { attribute mass; }" | windtrader export     # print element JSON graph
```

Subcommands:

```text
check    (default) parse-validate SysML text
echo     print the normalized/echoed representation
export   parse SysML and print the SysMLv2 element JSON graph (API shape)
```

Options:

```text
--version            Show windtrader package version
--java-version       windtrader-java version to use (default: 0.2.0)
--timeout            Subprocess timeout (default: 10s for check/echo, 120s for export)
```

The CLI forwards stdout/stderr directly from the Java tool and exits with the same exit code.

---

## Python API

> **0.2.0 rename:** `windtrader.validator` (module) / `WindtraderValidator` /
> `ValidationResult` are now `windtrader.client` / `WindtraderClient` /
> `CommandResult`. The module drives `check`, `echo`, and now `export`, so the
> old "validator" name was misleading. Update imports from `windtrader.validator`
> to `windtrader.client` and the class/type names accordingly.
>
> ```python
> # before (0.1.x)
> from windtrader.validator import WindtraderValidator, ValidationResult
> # after (0.2.0)
> from windtrader.client import WindtraderClient, CommandResult
> ```

### Basic validation

```python
from windtrader import validate

result = validate("part { attribute mass; }")

if result.ok:
    print("Valid SysML")
else:
    print("Invalid:", result.stderr)
```

### Client object

```python
from windtrader import WindtraderClient

client = WindtraderClient(version="0.2.0")
res = client.validate("part { attrib mass; }")

print(res.exit_code)  # 0 = valid, 2 = syntax error, 3 = runtime error
```

### Export

```python
from windtrader import export

res = export("part { attribute mass; }")

if res.ok:
    print(res.stdout)  # SysMLv2 element JSON graph (array of API-shaped elements)
else:
    print("Failed:", res.stderr)
```

### CommandResult

Returned objects include:

- `ok`: boolean success flag
- `exit_code`: Java exit code
- `stdout` / `stderr`: raw tool output
- `jar_path`: cached JAR location
- `duration_s`: execution time
- `is_invalid_syntax`
- `is_runtime_error`

---

## Exit Code Contract

The Java validator defines:

| Exit Code | Meaning            |
|----------:|--------------------|
| 0         | Valid syntax       |
| 2         | Invalid SysML      |
| 3         | Runtime error      |

Python preserves these codes exactly.

---

## Configuration

Environment variables:

- `WINDTRADER_CACHE_DIR` – override JAR cache directory
- `WINDTRADER_JAVA_REPO` – override GitHub repo for JAR downloads
- `WINDTRADER_JAVA_STABLE_ASSET` – explicit asset URL (optional)

---

## Design Philosophy

- **Grammar is authoritative**: validation truth lives in Java
- **Python is orchestration only**
- **No silent fallbacks**
- **Reproducible CI behavior**

This makes `windtrader` suitable as a foundation for:

- Code generators
- Corpus analysis
- Model-building libraries
- CI validation gates

---

## Relationship to Other Projects

`windtrader` is designed to act as the validation backbone for higher-level SysML tooling,
including programmatic builders and corpus-driven API generation pipelines.

---

## License

MIT License. See [LICENSE](LICENSE).

---

## Contributing

Pull requests welcome. Please ensure:

- CI passes
- Docstring coverage remains high
- Backend version bumps are intentional
