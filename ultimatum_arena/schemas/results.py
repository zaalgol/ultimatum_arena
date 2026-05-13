"""Round result schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RoundResult(BaseModel):
    """Full record of a single round, saved to storage."""

    round_index: int = Field(..., ge=0)

    # Pie truth
    true_pie: float
    claimed_pie: float
    offer: float
    public_message: str = ""

    # Responder decision
    accepted: bool

    # Audit
    audit_occurred: bool
    lie_detected: bool  # claimed_pie != true_pie AND audit_occurred

    # Payoffs (after penalties)
    proposer_payoff: float
    responder_payoff: float

    # Penalty detail
    lie_penalty: float = Field(default=0.0, description="Penalty deducted from proposer when lie is detected.")

    # Optional per-round metadata (e.g. raw LLM responses for observability)
    metadata: dict[str, Any] = Field(default_factory=dict)
