import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decimal import Decimal

from guardrails.engine import normalize_variance_pct, summarize_result_for_log


class TestSummarizeResultForLog:
    def test_non_dict_is_stringified(self):
        assert summarize_result_for_log("ok") == {"value": "ok"}

    def test_lists_become_count_plus_preview(self):
        result = summarize_result_for_log(
            {"campaign_id": 1, "calls": [{"id": n} for n in range(10)]}
        )
        assert result["campaign_id"] == 1
        assert result["calls"]["count"] == 10
        assert result["calls"]["preview"] == [{"id": 0}, {"id": 1}, {"id": 2}]

    def test_empty_list_preview_is_empty(self):
        result = summarize_result_for_log({"campaigns": []})
        assert result["campaigns"] == {"count": 0, "preview": []}

    def test_scalars_pass_through(self):
        payload = {"status": "auto_executed", "risk": {"final_score": 0.7}}
        assert summarize_result_for_log(payload) == payload


class TestNormalizeVariancePct:
    def test_quantizes_to_flagged_campaign_numeric_scale(self):
        assert normalize_variance_pct(48.7) == Decimal("48.70")

    def test_same_displayed_value_matches_regardless_of_float_repr(self):
        assert normalize_variance_pct(48.70) == normalize_variance_pct(48.7)
