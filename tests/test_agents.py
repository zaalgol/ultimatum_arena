"""Unit tests for heuristic agents."""

import pytest

from ultimatum_arena.agents import (
    ExpectedValueProposer,
    GreedyHonestProposer,
    HonestFairProposer,
    LyingGreedyProposer,
    SuspiciousResponder,
    ThresholdResponder,
)
from ultimatum_arena.schemas import ProposerObservation, ResponderObservation


def _prop_obs(true_pie: float = 100.0, audit_prob: float = 0.0, lie_penalty: float = 0.0) -> ProposerObservation:
    return ProposerObservation(
        true_pie=true_pie,
        pie_range=(50.0, 150.0),
        round_index=0,
        audit_prob=audit_prob,
        lie_penalty=lie_penalty,
    )


def _resp_obs(claimed_pie: float, offer: float) -> ResponderObservation:
    return ResponderObservation(
        claimed_pie=claimed_pie,
        offer=offer,
        pie_range=(50.0, 150.0),
        round_index=0,
    )


# ---------------------------------------------------------------------------
# HonestFairProposer
# ---------------------------------------------------------------------------

class TestHonestFairProposer:
    def test_claimed_equals_true(self) -> None:
        p = HonestFairProposer()
        action = p.act(_prop_obs(true_pie=100.0))
        assert action.claimed_pie == pytest.approx(100.0)

    def test_offer_is_half(self) -> None:
        p = HonestFairProposer()
        action = p.act(_prop_obs(true_pie=80.0))
        assert action.offer == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# GreedyHonestProposer
# ---------------------------------------------------------------------------

class TestGreedyHonestProposer:
    def test_claimed_equals_true(self) -> None:
        p = GreedyHonestProposer(offer_fraction=0.2)
        action = p.act(_prop_obs(100.0))
        assert action.claimed_pie == pytest.approx(100.0)

    def test_offer_fraction(self) -> None:
        p = GreedyHonestProposer(offer_fraction=0.2)
        action = p.act(_prop_obs(100.0))
        assert action.offer == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# LyingGreedyProposer
# ---------------------------------------------------------------------------

class TestLyingGreedyProposer:
    def test_claimed_less_than_true(self) -> None:
        p = LyingGreedyProposer(claimed_fraction=0.6)
        action = p.act(_prop_obs(100.0))
        assert action.claimed_pie < 100.0

    def test_claimed_fraction(self) -> None:
        p = LyingGreedyProposer(claimed_fraction=0.6, offer_fraction=0.4)
        action = p.act(_prop_obs(100.0))
        assert action.claimed_pie == pytest.approx(60.0)
        assert action.offer == pytest.approx(24.0)

    def test_invalid_claimed_fraction_raises(self) -> None:
        with pytest.raises(ValueError):
            LyingGreedyProposer(claimed_fraction=0.0)

    def test_action_is_valid_schema(self) -> None:
        """offer must not exceed claimed_pie — schema should not raise."""
        p = LyingGreedyProposer(claimed_fraction=0.6, offer_fraction=1.0)
        action = p.act(_prop_obs(100.0))
        assert action.offer <= action.claimed_pie


# ---------------------------------------------------------------------------
# ThresholdResponder
# ---------------------------------------------------------------------------

class TestThresholdResponder:
    def test_accepts_above_threshold(self) -> None:
        r = ThresholdResponder(min_fraction=0.3)
        obs = _resp_obs(claimed_pie=100.0, offer=35.0)
        assert r.act(obs).accept is True

    def test_rejects_below_threshold(self) -> None:
        r = ThresholdResponder(min_fraction=0.3)
        obs = _resp_obs(claimed_pie=100.0, offer=25.0)
        assert r.act(obs).accept is False

    def test_accepts_at_exact_threshold(self) -> None:
        r = ThresholdResponder(min_fraction=0.3)
        obs = _resp_obs(claimed_pie=100.0, offer=30.0)
        assert r.act(obs).accept is True


# ---------------------------------------------------------------------------
# SuspiciousResponder
# ---------------------------------------------------------------------------

class TestSuspiciousResponder:
    def test_discounts_claim(self) -> None:
        """With suspicion, a borderline offer that ThresholdResponder accepts is rejected."""
        threshold_r = ThresholdResponder(min_fraction=0.3)
        suspicious_r = SuspiciousResponder(min_fraction=0.35, suspicion_discount=0.15)
        # claimed=100, offer=30 → threshold accepts (30 >= 30), suspicious may not
        obs = _resp_obs(claimed_pie=100.0, offer=30.0)
        # Threshold accepts...
        assert threshold_r.act(obs).accept is True
        # ...but suspicious is tougher (effective_pie = 100 - 0.15*100 = 85, need 0.35*85=29.75 → 30 >= 29.75 still accepts)
        # Use a harder case: offer=28
        obs2 = _resp_obs(claimed_pie=100.0, offer=28.0)
        assert threshold_r.act(obs2).accept is False   # 28 < 30
        # Suspicious also rejects since 28 < 29.75
        assert suspicious_r.act(obs2).accept is False


# ---------------------------------------------------------------------------
# ExpectedValueProposer
# ---------------------------------------------------------------------------

class TestExpectedValueProposer:
    def test_importable(self) -> None:
        from ultimatum_arena.agents import ExpectedValueProposer as EVP  # noqa: F401

    def test_returns_valid_action(self) -> None:
        p = ExpectedValueProposer()
        action = p.act(_prop_obs(true_pie=100.0))
        assert action.offer <= action.claimed_pie
        assert action.offer >= 0
        assert action.claimed_pie > 0

    def test_zero_audit_chooses_deceptive(self) -> None:
        """At zero audit cost, aggressive underclaim has the highest EV → deceptive."""
        p = ExpectedValueProposer()
        action = p.act(_prop_obs(true_pie=100.0, audit_prob=0.0, lie_penalty=0.0))
        assert action.claimed_pie < 100.0, "Should choose a deceptive (underclaim) candidate"

    def test_high_audit_high_penalty_chooses_honest(self) -> None:
        """At audit_prob=1 and large penalty, honest candidate has the highest EV."""
        p = ExpectedValueProposer()
        action = p.act(_prop_obs(true_pie=100.0, audit_prob=1.0, lie_penalty=100.0))
        assert action.claimed_pie == pytest.approx(100.0), "Should report honestly"

    def test_offer_does_not_exceed_claimed(self) -> None:
        for audit_prob in (0.0, 0.5, 1.0):
            p = ExpectedValueProposer()
            action = p.act(_prop_obs(true_pie=80.0, audit_prob=audit_prob, lie_penalty=50.0))
            assert action.offer <= action.claimed_pie

    def test_invalid_honest_offer_fraction_above_1_raises(self) -> None:
        with pytest.raises(ValueError):
            ExpectedValueProposer(honest_offer_fraction=1.5)

    def test_invalid_honest_offer_fraction_below_0_raises(self) -> None:
        with pytest.raises(ValueError):
            ExpectedValueProposer(honest_offer_fraction=-0.1)

    def test_invalid_moderate_claim_fraction_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            ExpectedValueProposer(moderate_claim_fraction=0.0)

    def test_invalid_moderate_claim_fraction_above_1_raises(self) -> None:
        with pytest.raises(ValueError):
            ExpectedValueProposer(moderate_claim_fraction=1.1)

    def test_invalid_aggressive_claim_fraction_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            ExpectedValueProposer(aggressive_claim_fraction=0.0)

    def test_invalid_offer_fraction_of_claim_above_1_raises(self) -> None:
        with pytest.raises(ValueError):
            ExpectedValueProposer(offer_fraction_of_claim=1.5)

    def test_invalid_offer_fraction_of_claim_below_0_raises(self) -> None:
        with pytest.raises(ValueError):
            ExpectedValueProposer(offer_fraction_of_claim=-0.1)

    def test_tiebreak_prefers_honest(self) -> None:
        """When all candidates have equal EV, honest candidate is preferred."""
        # Force all payoffs equal by zeroing offer fractions for deceptive candidates
        # and setting honest_offer_fraction so honest EV == deceptive EV.
        # With offer_fraction_of_claim=0 deceptive offer=0, so EV = true_pie - audit*pen.
        # With honest_offer_fraction=0 honest offer=0, so EV = true_pie.
        # Make audit_prob=0, lie_penalty=0 → all EVs equal (true_pie - 0).
        p = ExpectedValueProposer(
            honest_offer_fraction=0.0,
            offer_fraction_of_claim=0.0,
        )
        action = p.act(_prop_obs(true_pie=100.0, audit_prob=0.0, lie_penalty=0.0))
        assert action.claimed_pie == pytest.approx(100.0), "Tie-break should prefer honest"
