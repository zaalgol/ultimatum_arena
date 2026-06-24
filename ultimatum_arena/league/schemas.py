"""Pydantic schemas and configs for the Reputation Network League.

The league wraps many one-shot :class:`~ultimatum_arena.envs.hidden_pie_audit.HiddenPieAuditEnv`
matches into a season played by a population of agents. These records capture
stable agent identity, evolving runtime state, per-match outcomes, private
memory, public gossip, and the configuration objects that make every component
deterministic and bounded.

Design notes
------------
* No raw LLM clients are stored on Pydantic records. Client/agent objects live
  on the runtime participant wrappers in :mod:`ultimatum_arena.league.agents`.
* Public reputation here is a **ground-truth evaluator** signal by default
  (the league scorekeeper sees ``true_pie``); set
  ``ReputationConfig.use_ground_truth=False`` for a public-information-only
  variant. This choice is documented and seedable, never hidden.
* An audit makes ``true_pie`` public for that match. Private memory and gossip
  therefore only know whether an opponent claimed truthfully when the match was
  audited; otherwise the truth stays hidden.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# Valid enum values, defined here (the schema boundary) so both the CLI and the
# Python API reject invalid conditions instead of silently mislabelling a run.
VALID_GOSSIP_MODES: frozenset[str] = frozenset({"off", "deterministic", "llm"})
VALID_MATCHING_POLICIES: frozenset[str] = frozenset({"random", "reputation_based"})


# ---------------------------------------------------------------------------
# Agent identity and runtime state
# ---------------------------------------------------------------------------


class LeagueAgentProfile(BaseModel):
    """Stable identity of a league participant (does not change during a season)."""

    agent_id: str
    display_name: str
    kind: str = "heuristic"  # heuristic | llm | mixed
    proposer_strategy: Optional[str] = None
    responder_mode: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class LeagueAgentState(BaseModel):
    """Evolving per-agent runtime state, updated after every match it plays."""

    profile: LeagueAgentProfile
    total_payoff: float = 0.0
    proposer_payoff: float = 0.0
    responder_payoff: float = 0.0
    matches_played: int = 0
    matches_as_proposer: int = 0
    matches_as_responder: int = 0
    accepted_matches: int = 0  # matches (as proposer) whose offer was accepted
    public_reputation: float = 50.0
    fairness_score: float = 0.0  # running mean of offer/true_pie over proposer matches
    deception_count: int = 0
    detected_lie_count: int = 0


# ---------------------------------------------------------------------------
# Match record
# ---------------------------------------------------------------------------


class LeagueMatchRecord(BaseModel):
    """Full, auditable record of one league match (one Hidden Pie Audit round)."""

    match_id: str
    season_index: int
    proposer_id: str
    responder_id: str
    true_pie: float
    claimed_pie: float
    offer: float
    public_message: str = ""
    accepted: bool
    audit_occurred: bool
    lie_detected: bool
    proposer_payoff: float
    responder_payoff: float
    proposer_reputation_before: float
    responder_reputation_before: float
    proposer_reputation_after: float
    responder_reputation_after: float
    status: str = "ok"  # ok | proposer_refusal | responder_refusal
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Private memory
# ---------------------------------------------------------------------------


class PrivateMemoryEntry(BaseModel):
    """One agent's private recollection of an interaction with an opponent.

    ``target_offer_ratio_true`` and ``target_claimed_truthfully`` are only known
    (non-``None``) when the match was audited, since an audit makes ``true_pie``
    public for that match. Otherwise the truth is hidden and they stay ``None``.
    """

    observer_id: str
    target_id: str
    match_id: str
    season_index: int
    target_role: str  # "proposer" or "responder" (role the *target* played)
    accepted: bool
    target_offer_ratio_claimed: Optional[float] = None
    target_offer_ratio_true: Optional[float] = None
    target_claimed_truthfully: Optional[bool] = None
    target_public_message: str = ""
    summary: str = ""


# ---------------------------------------------------------------------------
# Public gossip / reviews
# ---------------------------------------------------------------------------


class GossipRecord(BaseModel):
    """A short public review one agent publishes about an opponent after a match.

    Gossip is UNTRUSTED social information, not ground truth. ``rating`` is a
    bounded sentiment in ``[-1, 1]`` (higher = more positive).
    """

    review_id: str
    match_id: str
    season_index: int
    author_id: str
    target_id: str
    target_role: str
    text: str
    rating: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    created_at_match: int


# ---------------------------------------------------------------------------
# Configuration objects (all defaults keep components deterministic & bounded)
# ---------------------------------------------------------------------------


class ReputationConfig(BaseModel):
    """Deterministic, bounded public-reputation scoring config.

    Reputation is a rolling exponential moving average over per-match scores in
    ``[min_rep, max_rep]``. A proposer's score rewards sharing a fair share of
    the pie and penalises deception, detected lies, and prompt-attack markers.
    """

    initial: float = 50.0
    min_rep: float = 0.0
    max_rep: float = 100.0
    alpha: float = Field(default=0.3, ge=0.0, le=1.0)  # weight on the new match
    fair_share_target: float = Field(default=0.5, gt=0.0)  # share counted as fully fair
    deception_penalty: float = Field(default=0.3, ge=0.0)
    detected_lie_penalty: float = Field(default=0.3, ge=0.0)
    prompt_attack_penalty: float = Field(default=0.4, ge=0.0)
    use_ground_truth: bool = True  # False -> public-information-only reputation
    score_responders: bool = False  # default: reputation reflects proposer behaviour
    responder_alpha: float = Field(default=0.1, ge=0.0, le=1.0)


class MemoryConfig(BaseModel):
    """Private-memory retention config."""

    enabled: bool = True
    per_opponent_limit: int = Field(default=3, ge=0)


class GossipConfig(BaseModel):
    """Public gossip config. ``mode`` is one of off | deterministic | llm."""

    mode: str = "off"  # off | deterministic | llm
    visible_k: int = Field(default=3, ge=0)

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        if value not in VALID_GOSSIP_MODES:
            raise ValueError(
                f"Unknown gossip mode {value!r}. Valid: {sorted(VALID_GOSSIP_MODES)}"
            )
        return value


class LeagueConfig(BaseModel):
    """Top-level season configuration."""

    n_matches: int = Field(..., gt=0)
    matching_policy: str = "random"  # random | reputation_based
    pie_range: tuple[float, float] = (50.0, 150.0)
    audit_prob: float = Field(default=0.25, ge=0.0, le=1.0)
    lie_penalty: float = Field(default=25.0, ge=0.0)
    rng_seed: Optional[int] = None
    reputation: ReputationConfig = Field(default_factory=ReputationConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    gossip: GossipConfig = Field(default_factory=GossipConfig)

    @field_validator("matching_policy")
    @classmethod
    def _validate_matching_policy(cls, value: str) -> str:
        if value not in VALID_MATCHING_POLICIES:
            raise ValueError(
                f"Unknown matching policy {value!r}. Valid: {sorted(VALID_MATCHING_POLICIES)}"
            )
        return value
