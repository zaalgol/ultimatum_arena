"""Heuristic, base, and LLM-backed agent implementations."""

from ultimatum_arena.agents.base import BaseProposer, BaseResponder
from ultimatum_arena.agents.proposers import (
    HonestFairProposer,
    GreedyHonestProposer,
    LyingGreedyProposer,
)
from ultimatum_arena.agents.responders import ThresholdResponder, SuspiciousResponder

__all__ = [
    "BaseProposer",
    "BaseResponder",
    "HonestFairProposer",
    "GreedyHonestProposer",
    "LyingGreedyProposer",
    "ThresholdResponder",
    "SuspiciousResponder",
    "LLMProposer",
    "LLMResponder",
]


def __getattr__(name: str):
    """Lazily import LLM-backed agents to avoid circular imports."""
    if name in ("LLMProposer", "LLMResponder"):
        from ultimatum_arena.llm.agents import LLMProposer, LLMResponder  # noqa: PLC0415

        globals()["LLMProposer"] = LLMProposer
        globals()["LLMResponder"] = LLMResponder
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
