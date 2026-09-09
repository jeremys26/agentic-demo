"""
Heavy coverage on the risk-scoring guardrail (PLANNING.md §7) — the
safety-critical part of the whole system. compute_score() and policy.route()
are pure functions with no I/O, so every threshold boundary, the hard cap,
and each weighted input's contribution can be tested directly and cheaply.
The I/O-bound gather_*_inputs() functions (which call the sim services'
REST APIs and the MCP server's own DB) are NOT covered by an automated test
here or elsewhere in this suite — this file is deliberately scoped to the
deterministic math, which is where a bug would be most dangerous, but the
gathering logic itself (and guard_reallocate_budget/guard_request_creative_
refresh end to end) is a real coverage gap, not just an intentional scoping
choice, and worth closing with mocked-httpx integration tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from guardrails import policy
from guardrails.scoring import compute_score


class TestComputeScoreBasics:
    def test_all_zero_risk_inputs_score_zero(self):
        result = compute_score(magnitude_pct=0, confidence=1.0, recency_flag=False, vertical="insurance")
        assert result.final_score == 0.0
        assert result.decision == "auto_execute"

    def test_maximum_risk_inputs_score_capped_at_100(self):
        result = compute_score(
            magnitude_pct=100, confidence=0.0, recency_flag=True, vertical="medicare_advantage"
        )
        # base_score = 0.5*100 + 0.35*100 + 0.15*100 = 100; *1.4 would be 140,
        # must be capped at 100.
        assert result.base_score == 100.0
        assert result.final_score == 100.0
        assert result.decision == "blocked"

    def test_magnitude_pct_over_100_clamped_in_score_but_preserved_in_output(self):
        result = compute_score(magnitude_pct=119.35, confidence=1.0, recency_flag=False, vertical="insurance")
        assert result.magnitude_pct == 119.35  # preserved for transparency
        assert result.magnitude_score == 100.0  # clamped for scoring

    def test_negative_magnitude_clamped_to_zero(self):
        result = compute_score(magnitude_pct=-5, confidence=1.0, recency_flag=False, vertical="insurance")
        assert result.magnitude_score == 0.0

    def test_confidence_over_1_clamped(self):
        result = compute_score(magnitude_pct=0, confidence=1.5, recency_flag=False, vertical="insurance")
        assert result.confidence == 1.0
        assert result.confidence_score == 0.0

    def test_confidence_below_0_clamped(self):
        result = compute_score(magnitude_pct=0, confidence=-0.5, recency_flag=False, vertical="insurance")
        assert result.confidence == 0.0
        assert result.confidence_score == 100.0


class TestPerInputContribution:
    """Each of the four §7 inputs should move the score in isolation,
    confirming the weighting (0.5 magnitude / 0.35 confidence / 0.15 recency,
    then the regulatory multiplier) is wired correctly."""

    def test_magnitude_alone_contributes_half_weight(self):
        result = compute_score(magnitude_pct=100, confidence=1.0, recency_flag=False, vertical="insurance")
        assert result.base_score == 50.0  # 0.5 * 100

    def test_confidence_alone_contributes_035_weight(self):
        result = compute_score(magnitude_pct=0, confidence=0.0, recency_flag=False, vertical="insurance")
        assert result.base_score == 35.0  # 0.35 * 100

    def test_recency_alone_contributes_015_weight(self):
        result = compute_score(magnitude_pct=0, confidence=1.0, recency_flag=True, vertical="insurance")
        assert result.base_score == 15.0  # 0.15 * 100

    def test_higher_confidence_means_lower_risk(self):
        low_conf = compute_score(magnitude_pct=50, confidence=0.1, recency_flag=False, vertical="insurance")
        high_conf = compute_score(magnitude_pct=50, confidence=0.9, recency_flag=False, vertical="insurance")
        assert low_conf.final_score > high_conf.final_score

    def test_recency_flag_raises_score_relative_to_no_recency(self):
        not_recent = compute_score(magnitude_pct=50, confidence=1.0, recency_flag=False, vertical="insurance")
        recent = compute_score(magnitude_pct=50, confidence=1.0, recency_flag=True, vertical="insurance")
        assert recent.final_score > not_recent.final_score


class TestRegulatorySensitivity:
    def test_regulated_vertical_scores_higher_than_unregulated_for_same_inputs(self):
        unregulated = compute_score(magnitude_pct=50, confidence=0.5, recency_flag=True, vertical="insurance")
        regulated = compute_score(
            magnitude_pct=50, confidence=0.5, recency_flag=True, vertical="medicare_advantage"
        )
        assert regulated.regulatory_multiplier == policy.REGULATORY_MULTIPLIER
        assert unregulated.regulatory_multiplier == 1.0
        assert regulated.final_score == round(unregulated.final_score * policy.REGULATORY_MULTIPLIER, 2)

    def test_home_services_is_not_regulated(self):
        result = compute_score(magnitude_pct=50, confidence=0.5, recency_flag=False, vertical="home_services")
        assert result.regulatory_multiplier == 1.0


class TestRoutingThresholdBoundaries:
    """Exact boundary behavior of policy.route(), independent of how a
    particular combination of inputs happens to produce that score."""

    def test_score_just_under_auto_threshold_auto_executes(self):
        assert policy.route(policy.AUTO_EXECUTE_THRESHOLD - 0.01, hard_cap_exceeded=False) == "auto_execute"

    def test_score_exactly_at_auto_threshold_does_not_auto_execute(self):
        # Strict "<" per PLANNING.md §7 — the boundary itself belongs to the
        # approval tier, not auto-execute.
        assert policy.route(policy.AUTO_EXECUTE_THRESHOLD, hard_cap_exceeded=False) == "pending_approval"

    def test_score_just_under_block_threshold_is_pending_approval(self):
        assert policy.route(policy.BLOCK_THRESHOLD - 0.01, hard_cap_exceeded=False) == "pending_approval"

    def test_score_exactly_at_block_threshold_is_blocked(self):
        assert policy.route(policy.BLOCK_THRESHOLD, hard_cap_exceeded=False) == "blocked"

    def test_score_above_block_threshold_is_blocked(self):
        assert policy.route(policy.BLOCK_THRESHOLD + 10, hard_cap_exceeded=False) == "blocked"

    def test_low_score_zero_is_auto_execute(self):
        assert policy.route(0.0, hard_cap_exceeded=False) == "auto_execute"

    def test_block_threshold_takes_priority_over_hard_cap(self):
        # A blocked-tier score blocks outright regardless of the hard cap flag.
        assert policy.route(policy.BLOCK_THRESHOLD, hard_cap_exceeded=True) == "blocked"
        assert policy.route(policy.BLOCK_THRESHOLD, hard_cap_exceeded=False) == "blocked"


class TestHardCap:
    """The fixed, score-independent hard cap (PLANNING.md §7) — defense in
    depth against a bug in the scoring function itself. A low score alone
    must not be sufficient to auto-execute if the hard cap was exceeded."""

    def test_low_score_with_hard_cap_exceeded_does_not_auto_execute(self):
        result = compute_score(
            magnitude_pct=1, confidence=1.0, recency_flag=False, vertical="insurance", hard_cap_exceeded=True
        )
        assert result.final_score < policy.AUTO_EXECUTE_THRESHOLD
        assert result.decision == "pending_approval"

    def test_low_score_with_hard_cap_clear_does_auto_execute(self):
        result = compute_score(
            magnitude_pct=1, confidence=1.0, recency_flag=False, vertical="insurance", hard_cap_exceeded=False
        )
        assert result.decision == "auto_execute"

    def test_hard_cap_does_not_change_the_numeric_score_itself(self):
        with_cap = compute_score(
            magnitude_pct=20, confidence=0.8, recency_flag=False, vertical="insurance", hard_cap_exceeded=True
        )
        without_cap = compute_score(
            magnitude_pct=20, confidence=0.8, recency_flag=False, vertical="insurance", hard_cap_exceeded=False
        )
        assert with_cap.final_score == without_cap.final_score
        assert with_cap.decision != without_cap.decision

    def test_hard_cap_cannot_downgrade_an_already_blocked_score(self):
        result = compute_score(
            magnitude_pct=100, confidence=0.0, recency_flag=True, vertical="medicare_advantage",
            hard_cap_exceeded=True,
        )
        assert result.decision == "blocked"


class TestLiveDemoScenarioReplay:
    """Replays the three tiers exactly as verified live against the running
    stack during Phase 3 development, campaign 1 (Medicare Advantage –
    Southeast TV, baseline weekly spend ~$50,300)."""

    def test_small_well_supported_reallocation_auto_executes(self):
        # $500 of $50,300 baseline ≈ 0.99% magnitude, full confidence, no recency.
        result = compute_score(magnitude_pct=0.99, confidence=1.0, recency_flag=False, vertical="medicare_advantage")
        assert result.decision == "auto_execute"

    def test_mid_size_reallocation_on_recently_touched_campaign_needs_approval(self):
        # $20,000 of $50,300 baseline ≈ 39.78% magnitude, full confidence, recent.
        result = compute_score(
            magnitude_pct=39.78, confidence=1.0, recency_flag=True, vertical="medicare_advantage",
            hard_cap_exceeded=True,
        )
        assert result.decision == "pending_approval"

    def test_full_budget_reallocation_on_recently_touched_campaign_is_blocked(self):
        # $60,000 of $50,300 baseline ≈ 119% magnitude (clamped to 100), recent.
        result = compute_score(
            magnitude_pct=119.35, confidence=1.0, recency_flag=True, vertical="medicare_advantage",
            hard_cap_exceeded=True,
        )
        assert result.decision == "blocked"
