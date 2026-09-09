from graphql_api import _windowed_cpl


class TestWindowedCpl:
    def test_empty_is_none(self):
        assert _windowed_cpl([], 45) == (None, None)

    def test_blended_not_average_of_daily_cpl(self):
        rollups = [
            {"spend": "450", "leads": 10},
            {"spend": "900", "leads": 10},
        ]
        window_cpl, variance = _windowed_cpl(rollups, 45, window_days=7)
        assert window_cpl == 67.5
        assert variance == 50.0
