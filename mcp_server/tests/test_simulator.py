from datetime import date

from simulator import (
    DEFAULT_NEXT_DATE,
    build_creative_metrics,
    build_onesource_rollups,
    build_smartspot_spots,
    latest_rollup_date,
    next_sim_date,
)


class TestNextSimDate:
    def test_empty_history_starts_after_seed_window(self):
        assert next_sim_date([]) == DEFAULT_NEXT_DATE

    def test_advances_one_day_past_latest_rollup(self):
        rollups = [{"date": "2026-08-20"}, {"date": "2026-08-28"}]
        assert latest_rollup_date(rollups) == date(2026, 8, 28)
        assert next_sim_date(rollups) == date(2026, 8, 29)


class TestBuildOnesourceRollups:
    def test_flagged_campaign_stays_above_target(self):
        import random

        campaigns = [
            {"id": 1, "target_cpl": 45},
            {"id": 2, "target_cpl": 48},
        ]
        rng = random.Random(1)
        rows = build_onesource_rollups(campaigns, date(2026, 8, 29), rng)
        flagged = next(r for r in rows if r["campaign_id"] == 1)
        steady = next(r for r in rows if r["campaign_id"] == 2)
        assert flagged["leads"] <= 112
        assert flagged["cpl"] > 45
        assert abs(steady["cpl"] - 48) / 48 < 0.12


class TestBuildSmartspotSpots:
    def test_uses_unique_station_daypart_combos_from_latest(self):
        import random

        spots = [
            {"campaign_id": 1, "station": 1, "daypart": 1, "cost": 210, "creative_label": "CR-114"},
            {"campaign_id": 1, "station": 2, "daypart": 2, "cost": 95, "creative_label": "CR-114"},
            {"campaign_id": 1, "station": 1, "daypart": 1, "cost": 211, "creative_label": "CR-114"},
        ]
        rows = build_smartspot_spots(spots, date(2026, 8, 29), random.Random(1))
        keys = {(r["station_id"], r["daypart_id"]) for r in rows}
        assert keys == {(1, 1), (2, 2)}
        assert len(rows) == 2


class TestBuildCreativeMetrics:
    def test_continues_ctr_without_a_fatigue_score(self):
        import random

        latest = {1: {"ctr": 0.013, "conversion_rate": 0.04}}
        rows = build_creative_metrics(latest, date(2026, 8, 29), random.Random(1))
        assert len(rows) == 1
        assert "fatigue_score" not in rows[0]
        assert rows[0]["ctr"] <= 0.013
        assert set(rows[0]) == {"creative_id", "impressions", "ctr", "conversion_rate"}
