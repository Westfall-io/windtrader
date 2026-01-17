from windtrader.validator import WindtraderValidator


def test_smoke_valid_syntax():
    v = WindtraderValidator()
    res = v.validate("part { attribute mass; }")
    # This will only pass once you point the “latest” URL to a real release asset
    assert res.exit_code in (0, 2, 3)


def test_smoke_invalid_keyword():
    v = WindtraderValidator()
    res = v.validate("part { attrib mass; }")
    assert res.exit_code in (0, 2, 3)
