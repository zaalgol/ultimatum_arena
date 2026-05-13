"""Hidden Pie Ultimatum Game with Audit environment."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from ultimatum_arena.schemas import (
    ProposerAction,
    ProposerObservation,
    ResponderAction,
    ResponderObservation,
    RoundResult,
)


@dataclass
class HiddenPieAuditEnv:
    """
    One-shot ultimatum game where the proposer privately knows the true pie
    size and may misreport it to the responder.

    Parameters
    ----------
    pie_range:
        (min, max) from which true_pie is sampled each round if no
        explicit true_pie is supplied to ``step``.
    audit_prob:
        Probability that an audit is performed each round.
    lie_penalty:
        Fixed amount deducted from the proposer's payoff when a lie is
        detected (claimed_pie != true_pie and audit occurred).
    rng_seed:
        Seed for the internal RNG; ``None`` means non-deterministic.
    """

    pie_range: tuple[float, float] = (50.0, 150.0)
    audit_prob: float = 0.3
    lie_penalty: float = 20.0
    rng_seed: Optional[int] = None

    _rng: random.Random = field(init=False, repr=False)
    _round_index: int = field(init=False, repr=False, default=0)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.rng_seed)
        self._round_index = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset round counter (but keep RNG state)."""
        self._round_index = 0

    def proposer_observation(self, true_pie: Optional[float] = None) -> tuple[float, ProposerObservation]:
        """
        Sample (or accept) a true_pie and return the proposer's observation.

        Returns
        -------
        true_pie : float
            The ground-truth pie value for this round.
        obs : ProposerObservation
        """
        if true_pie is None:
            true_pie = round(self._rng.uniform(*self.pie_range), 2)
        obs = ProposerObservation(
            true_pie=true_pie,
            pie_range=self.pie_range,
            round_index=self._round_index,
            audit_prob=self.audit_prob,
            lie_penalty=self.lie_penalty,
        )
        return true_pie, obs

    def responder_observation(self, action: ProposerAction) -> ResponderObservation:
        """Build the responder's limited view from the proposer's action."""
        return ResponderObservation(
            claimed_pie=action.claimed_pie,
            offer=action.offer,
            public_message=action.public_message,
            pie_range=self.pie_range,
            round_index=self._round_index,
            audit_prob=self.audit_prob,
            lie_penalty=self.lie_penalty,
        )

    def step(
        self,
        true_pie: float,
        proposer_action: ProposerAction,
        responder_action: ResponderAction,
    ) -> RoundResult:
        """
        Resolve one round and return a full RoundResult.

        Payoff logic
        ------------
        - Rejection  → both players get 0 (before penalty).
        - Acceptance → proposer keeps (true_pie - offer), responder gets offer.
        - Lie detected → lie_penalty subtracted from proposer's payoff.
        """
        accepted = responder_action.accept
        audit_occurred = self._rng.random() < self.audit_prob
        lie_detected = (proposer_action.claimed_pie != true_pie) and audit_occurred

        if accepted:
            proposer_payoff = true_pie - proposer_action.offer
            responder_payoff = proposer_action.offer
        else:
            proposer_payoff = 0.0
            responder_payoff = 0.0

        penalty_applied = 0.0
        if lie_detected:
            penalty_applied = self.lie_penalty
            proposer_payoff -= penalty_applied

        result = RoundResult(
            round_index=self._round_index,
            true_pie=true_pie,
            claimed_pie=proposer_action.claimed_pie,
            offer=proposer_action.offer,
            public_message=proposer_action.public_message,
            accepted=accepted,
            audit_occurred=audit_occurred,
            lie_detected=lie_detected,
            proposer_payoff=proposer_payoff,
            responder_payoff=responder_payoff,
            lie_penalty=penalty_applied,
        )

        self._round_index += 1
        return result
