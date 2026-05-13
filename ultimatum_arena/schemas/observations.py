"""Observation schemas for proposer and responder."""

from pydantic import BaseModel, Field


class ProposerObservation(BaseModel):
    """What the proposer sees at the start of a round."""

    true_pie: float = Field(..., gt=0, description="The actual pie size, only visible to the proposer.")
    pie_range: tuple[float, float] = Field(
        ..., description="Public (min, max) range that both players know."
    )
    round_index: int = Field(..., ge=0)
    # Public game parameters — both players know these
    audit_prob: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability an audit fires each round.")
    lie_penalty: float = Field(default=0.0, ge=0.0, description="Penalty deducted from proposer when lie is detected.")


class ResponderObservation(BaseModel):
    """What the responder sees before deciding."""

    claimed_pie: float = Field(..., gt=0, description="Pie size the proposer claimed.")
    offer: float = Field(..., ge=0, description="Amount offered to the responder.")
    public_message: str = Field(default="")
    pie_range: tuple[float, float] = Field(
        ..., description="Public (min, max) range that both players know."
    )
    round_index: int = Field(..., ge=0)
    # Public game parameters — both players know these
    audit_prob: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability an audit fires each round.")
    lie_penalty: float = Field(default=0.0, ge=0.0, description="Penalty deducted from proposer when lie is detected.")
