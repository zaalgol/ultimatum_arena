"""Heuristic proposer agents."""

from dataclasses import dataclass

from ultimatum_arena.agents.base import BaseProposer
from ultimatum_arena.schemas import ProposerAction, ProposerObservation


class HonestFairProposer(BaseProposer):
    """Always reports true_pie accurately and offers exactly half."""

    def act(self, obs: ProposerObservation) -> ProposerAction:
        return ProposerAction(
            claimed_pie=obs.true_pie,
            offer=round(obs.true_pie / 2, 6),
        )


class GreedyHonestProposer(BaseProposer):
    """Reports true_pie accurately but keeps most of it.

    Parameters
    ----------
    offer_fraction:
        Fraction of the *true* pie offered to the responder. Default 0.2.
    """

    def __init__(self, offer_fraction: float = 0.2) -> None:
        self.offer_fraction = offer_fraction

    def act(self, obs: ProposerObservation) -> ProposerAction:
        return ProposerAction(
            claimed_pie=obs.true_pie,
            offer=round(obs.true_pie * self.offer_fraction, 6),
        )


class LyingGreedyProposer(BaseProposer):
    """Understates the pie to justify a low absolute offer.

    Strategy:
      - Claims ``claimed_fraction`` of true_pie as the pie size.
      - Offers ``offer_fraction`` of the *claimed* pie (honest-looking share).
    This keeps the ratio of offer/claimed_pie plausible while pocketing more.

    Parameters
    ----------
    claimed_fraction:
        How much of the real pie to claim (e.g. 0.6 → claims 60 % of actual).
    offer_fraction:
        Fraction of the *claimed* pie offered to the responder. Default 0.4.
    """

    def __init__(self, claimed_fraction: float = 0.6, offer_fraction: float = 0.4) -> None:
        if not (0 < claimed_fraction <= 1):
            raise ValueError("claimed_fraction must be in (0, 1]")
        self.claimed_fraction = claimed_fraction
        self.offer_fraction = offer_fraction

    def act(self, obs: ProposerObservation) -> ProposerAction:
        claimed = round(obs.true_pie * self.claimed_fraction, 6)
        offer = round(claimed * self.offer_fraction, 6)
        return ProposerAction(
            claimed_pie=claimed,
            offer=offer,
            public_message="",
        )


@dataclass(frozen=True)
class _Candidate:
    claimed_pie: float
    offer: float
    is_deceptive: bool


class ExpectedValueProposer(BaseProposer):
    """Deterministic proposer that picks the highest expected-value action.

    Evaluates three fixed candidates (honest, moderate underclaim, aggressive
    underclaim) and selects the one with the highest expected proposer payoff:

        honest:      true_pie - offer
        deceptive:   true_pie - offer - audit_prob * lie_penalty

    Tie-breaking is deterministic: prefer the least deceptive candidate.

    Parameters
    ----------
    honest_offer_fraction:
        Fraction of true_pie offered when reporting honestly. Default 0.45.
    moderate_claim_fraction:
        claimed_pie = moderate_claim_fraction * true_pie. Default 0.65.
    aggressive_claim_fraction:
        claimed_pie = aggressive_claim_fraction * true_pie. Default 0.55.
    offer_fraction_of_claim:
        Fraction of claimed_pie offered for deceptive candidates. Default 0.5.
    """

    def __init__(
        self,
        honest_offer_fraction: float = 0.45,
        moderate_claim_fraction: float = 0.65,
        aggressive_claim_fraction: float = 0.55,
        offer_fraction_of_claim: float = 0.5,
    ) -> None:
        if not (0.0 <= honest_offer_fraction <= 1.0):
            raise ValueError("honest_offer_fraction must be in [0, 1]")
        if not (0.0 < moderate_claim_fraction <= 1.0):
            raise ValueError("moderate_claim_fraction must be in (0, 1]")
        if not (0.0 < aggressive_claim_fraction <= 1.0):
            raise ValueError("aggressive_claim_fraction must be in (0, 1]")
        if not (0.0 <= offer_fraction_of_claim <= 1.0):
            raise ValueError("offer_fraction_of_claim must be in [0, 1]")
        self.honest_offer_fraction = honest_offer_fraction
        self.moderate_claim_fraction = moderate_claim_fraction
        self.aggressive_claim_fraction = aggressive_claim_fraction
        self.offer_fraction_of_claim = offer_fraction_of_claim

    def _candidates(self, true_pie: float) -> list[_Candidate]:
        honest_offer = round(true_pie * self.honest_offer_fraction, 6)
        moderate_claim = round(true_pie * self.moderate_claim_fraction, 6)
        aggressive_claim = round(true_pie * self.aggressive_claim_fraction, 6)
        return [
            _Candidate(claimed_pie=true_pie, offer=honest_offer, is_deceptive=False),
            _Candidate(
                claimed_pie=moderate_claim,
                offer=round(moderate_claim * self.offer_fraction_of_claim, 6),
                is_deceptive=True,
            ),
            _Candidate(
                claimed_pie=aggressive_claim,
                offer=round(aggressive_claim * self.offer_fraction_of_claim, 6),
                is_deceptive=True,
            ),
        ]

    def _expected_payoff(self, c: _Candidate, true_pie: float, audit_prob: float, lie_penalty: float) -> float:
        payoff = true_pie - c.offer
        if c.is_deceptive:
            payoff -= audit_prob * lie_penalty
        return payoff

    def act(self, obs: ProposerObservation) -> ProposerAction:
        candidates = self._candidates(obs.true_pie)
        # Sort: highest EV first; ties broken by preferring non-deceptive (False < True)
        best = max(
            candidates,
            key=lambda c: (
                self._expected_payoff(c, obs.true_pie, obs.audit_prob, obs.lie_penalty),
                -int(c.is_deceptive),  # honest preferred on tie
            ),
        )
        return ProposerAction(
            claimed_pie=best.claimed_pie,
            offer=best.offer,
            public_message=f"I claim a pie of {best.claimed_pie} and offer {best.offer}.",
        )
