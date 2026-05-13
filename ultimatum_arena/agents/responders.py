"""Heuristic responder agents."""

from ultimatum_arena.agents.base import BaseResponder
from ultimatum_arena.schemas import ResponderAction, ResponderObservation


class ThresholdResponder(BaseResponder):
    """Accepts if offer >= ``min_fraction`` of the *claimed* pie.

    Parameters
    ----------
    min_fraction:
        Minimum acceptable offer as a fraction of claimed_pie. Default 0.3.
    """

    def __init__(self, min_fraction: float = 0.3) -> None:
        self.min_fraction = min_fraction

    def act(self, obs: ResponderObservation) -> ResponderAction:
        threshold = obs.claimed_pie * self.min_fraction
        return ResponderAction(accept=obs.offer >= threshold)


class SuspiciousResponder(BaseResponder):
    """Discounts the claimed pie and applies a tougher threshold.

    Assumes the proposer may be lying by up to ``suspicion_discount`` of the
    pie range's max, and requires a higher fraction of the *discounted* claim.

    Heuristic
    ---------
    effective_pie = claimed_pie - suspicion_discount * (range_max - range_min)
    Accept iff offer >= min_fraction * effective_pie

    Parameters
    ----------
    min_fraction:
        Minimum acceptable fraction of the discounted pie. Default 0.35.
    suspicion_discount:
        How much the responder mentally subtracts (as a fraction of the range
        width). Default 0.15.
    """

    def __init__(self, min_fraction: float = 0.35, suspicion_discount: float = 0.15) -> None:
        self.min_fraction = min_fraction
        self.suspicion_discount = suspicion_discount

    def act(self, obs: ResponderObservation) -> ResponderAction:
        range_width = obs.pie_range[1] - obs.pie_range[0]
        effective_pie = obs.claimed_pie - self.suspicion_discount * range_width
        # Never let effective_pie drop below the offer itself
        effective_pie = max(effective_pie, obs.offer)
        threshold = effective_pie * self.min_fraction
        return ResponderAction(accept=obs.offer >= threshold)
