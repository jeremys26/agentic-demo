"""CTR decline vs this creative's own first-week average.

Not a stored score: baseline and recent CTR come from CreativePerformanceDaily.ctr,
which is itself responses ÷ impressions. A creative is declining when that drop
is at least DECLINE_THRESHOLD_PCT (the common ~20% refresh trigger).
"""

from statistics import fmean

DECLINE_THRESHOLD_PCT = 20.0
WINDOW_DAYS = 7


def _mean_ctr(values):
    if not values:
        return None
    return round(fmean(values), 4)


def summarize_ctr(daily_rows, threshold_pct=DECLINE_THRESHOLD_PCT):
    """Return baseline/recent CTR and decline % for an ordered list of daily rows.

    Each row needs a ``ctr`` field (Decimal or float). ``days_of_data`` is the
    number of rows passed in — the caller should pass the full history.
    """
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
