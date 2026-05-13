"""Action schemas for proposer and responder."""

from pydantic import BaseModel, Field, model_validator


class ProposerAction(BaseModel):
    """What the proposer sends each round."""

    claimed_pie: float = Field(..., gt=0, description="Pie size the proposer claims to the responder.")
    offer: float = Field(..., ge=0, description="Amount offered to the responder.")
    public_message: str = Field(default="", description="Optional free-text message visible to the responder.")

    @model_validator(mode="after")
    def offer_le_claimed(self) -> "ProposerAction":
        if self.offer > self.claimed_pie:
            raise ValueError("offer cannot exceed claimed_pie")
        return self


class ResponderAction(BaseModel):
    """What the responder sends each round."""

    accept: bool = Field(..., description="True to accept the offer, False to reject.")
