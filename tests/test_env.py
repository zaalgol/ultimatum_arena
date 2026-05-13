"""Unit tests for HiddenPieAuditEnv."""

import pytest

from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
from ultimatum_arena.schemas import ProposerAction, ResponderAction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(audit_prob: float = 0.0, lie_penalty: float = 20.0, seed: int = 0) -> HiddenPieAuditEnv:
    return HiddenPieAuditEnv(audit_prob=audit_prob, lie_penalty=lie_penalty, rng_seed=seed)


def _accept() -> ResponderAction:
    return ResponderAction(accept=True)


def _reject() -> ResponderAction:
    return ResponderAction(accept=False)


# ---------------------------------------------------------------------------
# Honest proposer is never marked as lying
# ---------------------------------------------------------------------------

class TestHonestProposerNotLying:
    def test_honest_no_audit(self) -> None:
        env = _env(audit_prob=0.0)
        true_pie = 100.0
        action = ProposerAction(claimed_pie=true_pie, offer=50.0)
        result = env.step(true_pie, action, _accept())
        assert not result.lie_detected

    def test_honest_with_audit(self) -> None:
        """Even with 100 % audit, honest proposer is NOT lie-detected."""
        env = _env(audit_prob=1.0)
        true_pie = 100.0
        action = ProposerAction(claimed_pie=true_pie, offer=50.0)
        result = env.step(true_pie, action, _accept())
        assert result.audit_occurred
        assert not result.lie_detected

    def test_lie_penalty_not_applied_to_honest(self) -> None:
        env = _env(audit_prob=1.0, lie_penalty=30.0)
        true_pie = 80.0
        action = ProposerAction(claimed_pie=true_pie, offer=40.0)
        result = env.step(true_pie, action, _accept())
        assert result.lie_penalty == 0.0


# ---------------------------------------------------------------------------
# Lying proposer detected only when audit happens
# ---------------------------------------------------------------------------

class TestLyingProposerDetection:
    def test_lie_not_detected_without_audit(self) -> None:
        env = _env(audit_prob=0.0)
        action = ProposerAction(claimed_pie=60.0, offer=20.0)
        result = env.step(true_pie=100.0, proposer_action=action, responder_action=_accept())
        assert not result.audit_occurred
        assert not result.lie_detected
        assert result.lie_penalty == 0.0

    def test_lie_detected_with_audit(self) -> None:
        env = _env(audit_prob=1.0)
        action = ProposerAction(claimed_pie=60.0, offer=20.0)
        result = env.step(true_pie=100.0, proposer_action=action, responder_action=_accept())
        assert result.audit_occurred
        assert result.lie_detected
        assert result.lie_penalty == env.lie_penalty

    def test_lie_penalty_deducted_from_proposer(self) -> None:
        penalty = 25.0
        env = _env(audit_prob=1.0, lie_penalty=penalty)
        true_pie = 100.0
        offer = 20.0
        action = ProposerAction(claimed_pie=60.0, offer=offer)
        result = env.step(true_pie, action, _accept())
        expected = (true_pie - offer) - penalty
        assert result.proposer_payoff == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Rejection gives both players zero (before penalties)
# ---------------------------------------------------------------------------

class TestRejection:
    def test_rejection_zero_payoffs_no_lie(self) -> None:
        env = _env(audit_prob=0.0)
        action = ProposerAction(claimed_pie=100.0, offer=30.0)
        result = env.step(100.0, action, _reject())
        assert not result.accepted
        assert result.proposer_payoff == 0.0
        assert result.responder_payoff == 0.0

    def test_rejection_zero_payoffs_even_with_lie_detected(self) -> None:
        """Lie penalty still applies on rejection + audit."""
        penalty = 20.0
        env = _env(audit_prob=1.0, lie_penalty=penalty)
        action = ProposerAction(claimed_pie=60.0, offer=20.0)
        result = env.step(100.0, action, _reject())
        assert not result.accepted
        assert result.responder_payoff == 0.0
        # proposer starts at 0 (rejected), then penalty applied
        assert result.proposer_payoff == pytest.approx(-penalty)


# ---------------------------------------------------------------------------
# Accepted offer gives correct payoffs
# ---------------------------------------------------------------------------

class TestAcceptedPayoffs:
    def test_proposer_keeps_remainder(self) -> None:
        env = _env(audit_prob=0.0)
        true_pie, offer = 100.0, 40.0
        action = ProposerAction(claimed_pie=true_pie, offer=offer)
        result = env.step(true_pie, action, _accept())
        assert result.proposer_payoff == pytest.approx(true_pie - offer)
        assert result.responder_payoff == pytest.approx(offer)

    def test_payoff_uses_true_pie_not_claimed(self) -> None:
        """Proposer's payoff is based on *true* pie, not claimed."""
        env = _env(audit_prob=0.0)
        true_pie, claimed, offer = 100.0, 60.0, 20.0
        action = ProposerAction(claimed_pie=claimed, offer=offer)
        result = env.step(true_pie, action, _accept())
        assert result.proposer_payoff == pytest.approx(true_pie - offer)

    def test_full_offer_gives_proposer_zero(self) -> None:
        env = _env(audit_prob=0.0)
        true_pie = 100.0
        action = ProposerAction(claimed_pie=true_pie, offer=true_pie)
        result = env.step(true_pie, action, _accept())
        assert result.proposer_payoff == pytest.approx(0.0)
        assert result.responder_payoff == pytest.approx(true_pie)


# ---------------------------------------------------------------------------
# Round index increments
# ---------------------------------------------------------------------------

def test_round_index_increments() -> None:
    env = _env()
    for i in range(3):
        _, obs = env.proposer_observation(true_pie=100.0)
        assert obs.round_index == i
        action = ProposerAction(claimed_pie=100.0, offer=50.0)
        env.step(100.0, action, _accept())


def test_reset_resets_round_index() -> None:
    env = _env()
    for _ in range(5):
        _, obs = env.proposer_observation(true_pie=100.0)
        action = ProposerAction(claimed_pie=100.0, offer=50.0)
        env.step(100.0, action, _accept())
    env.reset()
    _, obs = env.proposer_observation(true_pie=100.0)
    assert obs.round_index == 0


# ---------------------------------------------------------------------------
# True pie is sampled at two-decimal monetary precision
# ---------------------------------------------------------------------------

class TestTruePieRounding:
    def test_sampled_true_pie_is_rounded_to_two_decimals(self) -> None:
        """Sampled true_pie must have at most 2 decimal places."""
        env = HiddenPieAuditEnv(rng_seed=99)
        for _ in range(20):
            true_pie, _ = env.proposer_observation()
            assert true_pie == round(true_pie, 2)

    def test_exact_claim_not_lie_detected_under_full_audit(self) -> None:
        """Claiming exactly the sampled true_pie is never counted as deception."""
        env = _env(audit_prob=1.0)
        true_pie, _ = env.proposer_observation()  # sampled, rounded to 2dp
        action = ProposerAction(claimed_pie=true_pie, offer=round(true_pie / 2, 2))
        result = env.step(true_pie, action, _accept())
        assert result.audit_occurred
        assert not result.lie_detected
        assert result.lie_penalty == 0.0

    def test_materially_different_claim_is_lie_detected(self) -> None:
        """A claim that differs by more than rounding is still flagged as a lie."""
        env = _env(audit_prob=1.0)
        true_pie = 100.0  # exact, 2-decimal safe
        action = ProposerAction(claimed_pie=90.0, offer=20.0)  # clearly different
        result = env.step(true_pie, action, _accept())
        assert result.audit_occurred
        assert result.lie_detected
