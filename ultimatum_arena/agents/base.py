"""Abstract base classes for proposer and responder agents.

Keep this interface minimal so LLM agents can subclass cleanly later.
"""

from abc import ABC, abstractmethod

from ultimatum_arena.schemas import (
    ProposerAction,
    ProposerObservation,
    ResponderAction,
    ResponderObservation,
    RoundResult,
)


class BaseProposer(ABC):
    """An agent that observes the true pie and produces an action."""

    @abstractmethod
    def act(self, obs: ProposerObservation) -> ProposerAction:
        """Return a ProposerAction given the current observation."""

    def on_round_result(self, result: RoundResult) -> None:
        """Optional callback — called after each round with the full result."""


class BaseResponder(ABC):
    """An agent that observes the proposer's claim and decides to accept/reject."""

    @abstractmethod
    def act(self, obs: ResponderObservation) -> ResponderAction:
        """Return a ResponderAction given the current observation."""

    def on_round_result(self, result: RoundResult) -> None:
        """Optional callback — called after each round with the full result."""
