import os
import pytest

from windtrader import validate_latest


@pytest.mark.skipif(os.environ.get("WINDTRADER_SMOKE") != "1", reason="requires bundled jar + java")
def test_validate_smoke():
    # Use a tiny snippet that your validator accepts.
    text = "part Stage_1 { attribute mass; }\n"
    validate_latest(text)
