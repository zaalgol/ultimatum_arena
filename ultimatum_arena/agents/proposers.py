"""Heuristic proposer agents."""

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
