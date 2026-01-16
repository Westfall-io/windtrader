from windtrader import available_versions, latest_version


def test_versions_present():
    assert latest_version()
    assert isinstance(available_versions(), list)
