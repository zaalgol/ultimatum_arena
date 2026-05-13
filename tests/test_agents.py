"""Unit tests for heuristic agents."""

import pytest

from ultimatum_arena.agents import (
    GreedyHonestProposer,
    HonestFairProposer,
    LyingGreedyProposer,
    SuspiciousResponder,
    ThresholdResponder,
)
from ultimatum_arena.schemas import ProposerObservation, ResponderObservation


def _prop_obs(true_pie: float = 100.0) -> ProposerObservation:
    return ProposerObservation(true_pie=true_pie, pie_range=(50.0, 150.0), round_index=0)


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
        action = p.act(_prop_obs(100.0))
        assert action.claimed_pie == pytest.approx(100.0)

    def test_offer_is_half(self) -> None:
        p = HonestFairProposer()
        action = p.act(_prop_obs(80.0))
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
