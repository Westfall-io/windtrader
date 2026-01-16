# windtrader

Python wrapper for SysMLv2 validation using bundled Java validator jar(s).

## Install
```bash
pip install windtrader
```

## Quick Use
```bash
from windtrader import validate_latest, compatibility_report

text = "part Stage_1 { attribute mass; }"

validate_latest(text)

r = compatibility_report(text)
print(r.status, r.latest_version, r.valid_versions)
```

## CLI
```bash
windtrader versions
windtrader check path/to/model.sysml
windtrader compat path/to/model.sysml
```

