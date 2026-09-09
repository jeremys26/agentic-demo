"""Keep in sync with services/captivator360/creatives/metrics.py.

CI only installs the MCP server package, so this file copies the formula
instead of importing Captivator360.
"""

from statistics import fmean

DECLINE_THRESHOLD_PCT = 20.0
WINDOW_DAYS = 7


def _mean_ctr(values):
    if not values:
        return None
    return round(fmean(values), 4)


def summarize_ctr(daily_rows, threshold_pct=DECLINE_THRESHOLD_PCT):
    ctrs = [float(row["ctr"]) for row in daily_rows if row.get("ctr") is not None]
    latest_ctr = round(ctrs[-1], 4) if ctrs else None
    empty = {
        "latest_ctr": latest_ctr,
        "baseline_ctr": _mean_ctr(ctrs) if ctrs else None,
        "recent_ctr": latest_ctr,
        "ctr_decline_pct": None,
        "declining": False,
        "decline_threshold_pct": threshold_pct,
    }
    if len(ctrs) < 2:
        return empty

    baseline = _mean_ctr(ctrs[:WINDOW_DAYS])
    recent = _mean_ctr(ctrs[-WINDOW_DAYS:])
    if not baseline:
        return {**empty, "baseline_ctr": baseline, "recent_ctr": recent}

    decline = round((baseline - recent) / baseline * 100, 1)
    return {
        "latest_ctr": latest_ctr,
        "baseline_ctr": baseline,
        "recent_ctr": recent,
        "ctr_decline_pct": decline,
        "declining": decline >= threshold_pct,
        "decline_threshold_pct": threshold_pct,
    }


class TestSummarizeCtr:
    def test_empty_is_not_declining(self):
        summary = summarize_ctr([])
        assert summary["ctr_decline_pct"] is None
        assert summary["declining"] is False

    def test_first_week_vs_last_week_crosses_refresh_trigger(self):
        rows = [{"ctr": 0.021}] * 7 + [{"ctr": 0.018}] * 14 + [{"ctr": 0.013}] * 7
        summary = summarize_ctr(rows)
        assert summary["baseline_ctr"] == 0.021
        assert summary["recent_ctr"] == 0.013
        assert summary["ctr_decline_pct"] == 38.1
        assert summary["declining"] is True
        assert summary["ctr_decline_pct"] >= DECLINE_THRESHOLD_PCT

    def test_flat_ctr_is_stable(self):
        summary = summarize_ctr([{"ctr": 0.02}] * 14)
        assert summary["ctr_decline_pct"] == 0.0
        assert summary["declining"] is False
