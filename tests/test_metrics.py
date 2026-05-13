"""Unit tests for compute_metrics."""

import pytest

from ultimatum_arena.analysis.metrics import compute_metrics
from ultimatum_arena.schemas import RoundResult


def _result(
    *,
    round_index: int = 0,
    true_pie: float = 100.0,
    claimed_pie: float = 100.0,
    offer: float = 50.0,
    accepted: bool = True,
    audit_occurred: bool = False,
    lie_detected: bool = False,
    proposer_payoff: float = 50.0,
    responder_payoff: float = 50.0,
    lie_penalty: float = 0.0,
) -> RoundResult:
    return RoundResult(
        round_index=round_index,
        true_pie=true_pie,
        claimed_pie=claimed_pie,
        offer=offer,
        accepted=accepted,
        audit_occurred=audit_occurred,
        lie_detected=lie_detected,
        proposer_payoff=proposer_payoff,
        responder_payoff=responder_payoff,
        lie_penalty=lie_penalty,
    )


class TestComputeMetrics:
    def test_empty_returns_empty(self) -> None:
        assert compute_metrics([]) == {}

    def test_n_rounds(self) -> None:
        results = [_result(round_index=i) for i in range(5)]
        assert compute_metrics(results)["n_rounds"] == 5

    def test_acceptance_rate_all_accepted(self) -> None:
        results = [_result(accepted=True) for _ in range(4)]
        assert compute_metrics(results)["acceptance_rate"] == pytest.approx(1.0)

    def test_acceptance_rate_half(self) -> None:
        results = [_result(accepted=True), _result(accepted=False)]
        assert compute_metrics(results)["acceptance_rate"] == pytest.approx(0.5)

    def test_deception_rate_all_honest(self) -> None:
        results = [_result(true_pie=100.0, claimed_pie=100.0) for _ in range(3)]
        assert compute_metrics(results)["deception_rate"] == pytest.approx(0.0)

    def test_deception_rate_all_lying(self) -> None:
        results = [_result(true_pie=100.0, claimed_pie=60.0) for _ in range(3)]
        assert compute_metrics(results)["deception_rate"] == pytest.approx(1.0)

    def test_mean_offer(self) -> None:
        results = [_result(offer=20.0), _result(offer=40.0)]
        assert compute_metrics(results)["mean_offer"] == pytest.approx(30.0)

    def test_mean_offer_ratio_true(self) -> None:
        # offer=50, true=100 → 0.5
        results = [_result(offer=50.0, true_pie=100.0)]
        assert compute_metrics(results)["mean_offer_ratio_true"] == pytest.approx(0.5)

    def test_mean_offer_ratio_claimed(self) -> None:
        # offer=20, claimed=80 → 0.25
        results = [_result(offer=20.0, claimed_pie=80.0)]
        assert compute_metrics(results)["mean_offer_ratio_claimed"] == pytest.approx(0.25)

    def test_detected_lie_rate(self) -> None:
        results = [
            _result(lie_detected=True),
            _result(lie_detected=False),
            _result(lie_detected=True),
            _result(lie_detected=True),
        ]
        assert compute_metrics(results)["detected_lie_rate"] == pytest.approx(0.75)

    def test_total_and_mean_payoffs(self) -> None:
        results = [
            _result(proposer_payoff=60.0, responder_payoff=40.0),
            _result(proposer_payoff=30.0, responder_payoff=20.0),
        ]
        m = compute_metrics(results)
        assert m["proposer_total_payoff"] == pytest.approx(90.0)
        assert m["responder_total_payoff"] == pytest.approx(60.0)
        assert m["proposer_mean_payoff"] == pytest.approx(45.0)
        assert m["responder_mean_payoff"] == pytest.approx(30.0)

    def test_audit_rate(self) -> None:
        results = [
            _result(audit_occurred=True),
            _result(audit_occurred=True),
            _result(audit_occurred=False),
        ]
        assert compute_metrics(results)["audit_rate"] == pytest.approx(2 / 3)


class TestPhase1ResearchMetrics:
    # ------------------------------------------------------------------
    # mean_lie_size
    # ------------------------------------------------------------------

    def test_mean_lie_size_zero_when_honest(self) -> None:
        results = [_result(true_pie=100.0, claimed_pie=100.0) for _ in range(3)]
        assert compute_metrics(results)["mean_lie_size"] == pytest.approx(0.0)

    def test_mean_lie_size_positive_understatement(self) -> None:
        # true=100, claimed=60 → lie_size=40 each round
        results = [_result(true_pie=100.0, claimed_pie=60.0) for _ in range(2)]
        assert compute_metrics(results)["mean_lie_size"] == pytest.approx(40.0)

    def test_mean_lie_size_negative_overstatement(self) -> None:
        # overclaiming: true=80, claimed=100 → lie_size = -20
        results = [_result(true_pie=80.0, claimed_pie=100.0, offer=40.0)]
        assert compute_metrics(results)["mean_lie_size"] == pytest.approx(-20.0)

    def test_mean_lie_size_mixed(self) -> None:
        # round1: lie_size=40, round2: lie_size=0 → mean=20
        results = [
            _result(true_pie=100.0, claimed_pie=60.0),
            _result(true_pie=100.0, claimed_pie=100.0),
        ]
        assert compute_metrics(results)["mean_lie_size"] == pytest.approx(20.0)

    # ------------------------------------------------------------------
    # mean_absolute_lie_size
    # ------------------------------------------------------------------

    def test_mean_absolute_lie_size_zero_when_honest(self) -> None:
        results = [_result(true_pie=100.0, claimed_pie=100.0) for _ in range(3)]
        assert compute_metrics(results)["mean_absolute_lie_size"] == pytest.approx(0.0)

    def test_mean_absolute_lie_size_understatement(self) -> None:
        results = [_result(true_pie=100.0, claimed_pie=60.0)]
        assert compute_metrics(results)["mean_absolute_lie_size"] == pytest.approx(40.0)

    def test_mean_absolute_lie_size_overstatement(self) -> None:
        # overclaiming: |lie_size| = |-20| = 20
        results = [_result(true_pie=80.0, claimed_pie=100.0, offer=40.0)]
        assert compute_metrics(results)["mean_absolute_lie_size"] == pytest.approx(20.0)

    def test_mean_absolute_lie_size_cancellation(self) -> None:
        # round1: lie_size=+40, round2: lie_size=-40 → mean_lie_size=0 but absolute=40
        results = [
            _result(true_pie=100.0, claimed_pie=60.0),
            _result(true_pie=80.0, claimed_pie=120.0, offer=40.0),
        ]
        m = compute_metrics(results)
        assert m["mean_lie_size"] == pytest.approx(0.0)
        assert m["mean_absolute_lie_size"] == pytest.approx(40.0)

    # ------------------------------------------------------------------
    # mean_relative_lie_size
    # ------------------------------------------------------------------

    def test_mean_relative_lie_size_zero_when_honest(self) -> None:
        results = [_result(true_pie=100.0, claimed_pie=100.0) for _ in range(3)]
        assert compute_metrics(results)["mean_relative_lie_size"] == pytest.approx(0.0)

    def test_mean_relative_lie_size_value(self) -> None:
        # true=100, claimed=60 → (100-60)/100 = 0.4
        results = [_result(true_pie=100.0, claimed_pie=60.0)]
        assert compute_metrics(results)["mean_relative_lie_size"] == pytest.approx(0.4)

    def test_mean_relative_lie_size_mixed(self) -> None:
        # round1: (100-60)/100=0.4, round2: 0/100=0.0 → mean=0.2
        results = [
            _result(true_pie=100.0, claimed_pie=60.0),
            _result(true_pie=100.0, claimed_pie=100.0),
        ]
        assert compute_metrics(results)["mean_relative_lie_size"] == pytest.approx(0.2)

    # ------------------------------------------------------------------
    # mean_offer_gap_from_fair_true_split
    # ------------------------------------------------------------------

    def test_offer_gap_true_zero_at_fair(self) -> None:
        # offer = true_pie/2 = 50 → gap = 0
        results = [_result(true_pie=100.0, offer=50.0)]
        assert compute_metrics(results)["mean_offer_gap_from_fair_true_split"] == pytest.approx(0.0)

    def test_offer_gap_true_below_fair(self) -> None:
        # offer=30, fair=50 → gap=20
        results = [_result(true_pie=100.0, offer=30.0)]
        assert compute_metrics(results)["mean_offer_gap_from_fair_true_split"] == pytest.approx(20.0)

    def test_offer_gap_true_above_fair(self) -> None:
        # offer=70, fair=50 → gap=20 (abs)
        results = [_result(true_pie=100.0, offer=70.0)]
        assert compute_metrics(results)["mean_offer_gap_from_fair_true_split"] == pytest.approx(20.0)

    def test_offer_gap_true_mean(self) -> None:
        # round1: gap=20, round2: gap=0 → mean=10
        results = [
            _result(true_pie=100.0, offer=30.0),
            _result(true_pie=100.0, offer=50.0),
        ]
        assert compute_metrics(results)["mean_offer_gap_from_fair_true_split"] == pytest.approx(10.0)

    # ------------------------------------------------------------------
    # mean_offer_gap_from_fair_claimed_split
    # ------------------------------------------------------------------

    def test_offer_gap_claimed_zero_at_fair(self) -> None:
        results = [_result(claimed_pie=80.0, offer=40.0)]
        assert compute_metrics(results)["mean_offer_gap_from_fair_claimed_split"] == pytest.approx(0.0)

    def test_offer_gap_claimed_nonzero(self) -> None:
        # offer=20, claimed=80, fair=40 → gap=20
        results = [_result(true_pie=100.0, claimed_pie=80.0, offer=20.0)]
        assert compute_metrics(results)["mean_offer_gap_from_fair_claimed_split"] == pytest.approx(20.0)

    def test_offer_gap_claimed_differs_from_true_gap(self) -> None:
        # true=100 (fair_true=50), claimed=60 (fair_claimed=30), offer=20
        # gap_true = |20-50| = 30, gap_claimed = |20-30| = 10
        results = [_result(true_pie=100.0, claimed_pie=60.0, offer=20.0)]
        m = compute_metrics(results)
        assert m["mean_offer_gap_from_fair_true_split"] == pytest.approx(30.0)
        assert m["mean_offer_gap_from_fair_claimed_split"] == pytest.approx(10.0)

    # ------------------------------------------------------------------
    # proposer_advantage
    # ------------------------------------------------------------------

    def test_proposer_advantage_zero_when_equal(self) -> None:
        results = [_result(proposer_payoff=50.0, responder_payoff=50.0)]
        assert compute_metrics(results)["proposer_advantage"] == pytest.approx(0.0)

    def test_proposer_advantage_positive(self) -> None:
        results = [_result(proposer_payoff=70.0, responder_payoff=30.0)]
        assert compute_metrics(results)["proposer_advantage"] == pytest.approx(40.0)

    def test_proposer_advantage_negative(self) -> None:
        results = [_result(proposer_payoff=20.0, responder_payoff=80.0)]
        assert compute_metrics(results)["proposer_advantage"] == pytest.approx(-60.0)

    def test_proposer_advantage_consistent_with_mean_payoffs(self) -> None:
        results = [
            _result(proposer_payoff=60.0, responder_payoff=40.0),
            _result(proposer_payoff=40.0, responder_payoff=20.0),
        ]
        m = compute_metrics(results)
        assert m["proposer_advantage"] == pytest.approx(
            m["proposer_mean_payoff"] - m["responder_mean_payoff"]
        )

    # ------------------------------------------------------------------
    # responder_mean_share_of_true_pie
    # ------------------------------------------------------------------

    def test_responder_mean_share_zero_when_rejected(self) -> None:
        results = [_result(responder_payoff=0.0, true_pie=100.0)]
        assert compute_metrics(results)["responder_mean_share_of_true_pie"] == pytest.approx(0.0)

    def test_responder_mean_share_half(self) -> None:
        # responder gets 50 of true_pie=100 → share=0.5
        results = [_result(responder_payoff=50.0, true_pie=100.0)]
        assert compute_metrics(results)["responder_mean_share_of_true_pie"] == pytest.approx(0.5)

    def test_responder_mean_share_with_lie(self) -> None:
        # proposer claimed 60, offered 24; true=100 → responder share = 24/100 = 0.24
        results = [_result(true_pie=100.0, claimed_pie=60.0, offer=24.0, responder_payoff=24.0)]
        assert compute_metrics(results)["responder_mean_share_of_true_pie"] == pytest.approx(0.24)

    def test_responder_mean_share_mean_across_rounds(self) -> None:
        # round1: 50/100=0.5, round2: 20/100=0.2 → mean=0.35
        results = [
            _result(responder_payoff=50.0, true_pie=100.0),
            _result(responder_payoff=20.0, true_pie=100.0),
        ]
        assert compute_metrics(results)["responder_mean_share_of_true_pie"] == pytest.approx(0.35)

    # ------------------------------------------------------------------
    # lie_detection_rate_among_lies
    # ------------------------------------------------------------------

    def test_lie_detection_rate_among_lies_zero_when_no_deception(self) -> None:
        results = [_result(true_pie=100.0, claimed_pie=100.0) for _ in range(4)]
        assert compute_metrics(results)["lie_detection_rate_among_lies"] == pytest.approx(0.0)

    def test_lie_detection_rate_among_lies_all_detected(self) -> None:
        results = [
            _result(true_pie=100.0, claimed_pie=60.0, lie_detected=True)
            for _ in range(3)
        ]
        assert compute_metrics(results)["lie_detection_rate_among_lies"] == pytest.approx(1.0)

    def test_lie_detection_rate_among_lies_partial(self) -> None:
        # 1 detected out of 3 deceptive rounds
        results = [
            _result(true_pie=100.0, claimed_pie=60.0, lie_detected=True),
            _result(true_pie=100.0, claimed_pie=60.0, lie_detected=False),
            _result(true_pie=100.0, claimed_pie=60.0, lie_detected=False),
        ]
        assert compute_metrics(results)["lie_detection_rate_among_lies"] == pytest.approx(1 / 3)

    def test_lie_detection_rate_among_lies_ignores_honest_rounds(self) -> None:
        # 2 honest + 1 deceptive detected → rate = 1/1 = 1.0, not 1/3
        results = [
            _result(true_pie=100.0, claimed_pie=100.0),
            _result(true_pie=100.0, claimed_pie=100.0),
            _result(true_pie=100.0, claimed_pie=60.0, lie_detected=True),
        ]
        assert compute_metrics(results)["lie_detection_rate_among_lies"] == pytest.approx(1.0)

    def test_lie_detection_rate_honest_lie_detected_flag_does_not_inflate(self) -> None:
        """An inconsistent honest round (claimed==true but lie_detected=True) must not
        inflate lie_detection_rate_among_lies above the actual deceptive-detection rate."""
        # honest round with lie_detected=True (inconsistent / malformed data)
        # deceptive round with lie_detected=False
        # correct rate = 0 detected deceptive / 1 deceptive round = 0.0
        results = [
            _result(true_pie=100.0, claimed_pie=100.0, lie_detected=True),
            _result(true_pie=100.0, claimed_pie=60.0, lie_detected=False),
        ]
        assert compute_metrics(results)["lie_detection_rate_among_lies"] == pytest.approx(0.0)

    # ------------------------------------------------------------------
    # Zero-denominator safety (P1 fix: _safe_div guards)
    # ------------------------------------------------------------------

    def test_zero_true_pie_does_not_crash(self) -> None:
        """Metrics that divide by true_pie must not raise ZeroDivisionError."""
        results = [_result(true_pie=0.0, claimed_pie=0.0, offer=0.0)]
        m = compute_metrics(results)
        assert m["mean_offer_ratio_true"] == pytest.approx(0.0)
        assert m["mean_relative_lie_size"] == pytest.approx(0.0)
        assert m["responder_mean_share_of_true_pie"] == pytest.approx(0.0)

    def test_zero_claimed_pie_does_not_crash(self) -> None:
        """mean_offer_ratio_claimed must not raise ZeroDivisionError."""
        results = [_result(true_pie=100.0, claimed_pie=0.0, offer=0.0)]
        m = compute_metrics(results)
        assert m["mean_offer_ratio_claimed"] == pytest.approx(0.0)
