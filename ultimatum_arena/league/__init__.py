"""Reputation Network League: a season layer over one-shot Hidden Pie Audit matches.

A population of agents plays many one-shot Hidden Pie Audit matches across a
season. Agents accumulate payoff, a bounded public reputation, private memory of
opponents, and (optionally) publish public gossip. Match-making can be random or
reputation-based. The league is built entirely on top of the existing one-shot
game, agents, LLM clients, and metrics — it does not modify them.
"""

from ultimatum_arena.league.agents import (
    HeuristicParticipant,
    LeagueParticipant,
    LLMParticipant,
)
from ultimatum_arena.league.gossip import (
    GossipStore,
    deterministic_review,
    llm_review,
)
from ultimatum_arena.league.matching import (
    VALID_MATCHING_POLICIES,
    build_schedule,
    select_pair,
)
from ultimatum_arena.league.memory import (
    PrivateMemoryStore,
    build_memory_entry,
)
from ultimatum_arena.league.metrics import compute_league_metrics
from ultimatum_arena.league.prompts import (
    LeagueContext,
    build_league_proposer_prompt,
    build_league_responder_prompt,
    format_league_context_block,
)
from ultimatum_arena.league.reputation import (
    apply_match_to_state,
    proposer_match_score,
    responder_match_score,
    update_reputation,
)
from ultimatum_arena.league.runner import LeagueResult, run_reputation_league
from ultimatum_arena.league.schemas import (
    VALID_GOSSIP_MODES,
    GossipConfig,
    GossipRecord,
    LeagueAgentProfile,
    LeagueAgentState,
    LeagueConfig,
    LeagueMatchRecord,
    MemoryConfig,
    PrivateMemoryEntry,
    ReputationConfig,
)
from ultimatum_arena.league.storage import write_league_outputs

__all__ = [
    # schemas
    "LeagueAgentProfile",
    "LeagueAgentState",
    "LeagueMatchRecord",
    "PrivateMemoryEntry",
    "GossipRecord",
    "ReputationConfig",
    "MemoryConfig",
    "GossipConfig",
    "LeagueConfig",
    "VALID_GOSSIP_MODES",
    # reputation
    "proposer_match_score",
    "responder_match_score",
    "update_reputation",
    "apply_match_to_state",
    # memory
    "PrivateMemoryStore",
    "build_memory_entry",
    # matching
    "select_pair",
    "build_schedule",
    "VALID_MATCHING_POLICIES",
    # gossip
    "GossipStore",
    "deterministic_review",
    "llm_review",
    # prompts
    "LeagueContext",
    "format_league_context_block",
    "build_league_proposer_prompt",
    "build_league_responder_prompt",
    # agents
    "LeagueParticipant",
    "HeuristicParticipant",
    "LLMParticipant",
    # metrics
    "compute_league_metrics",
    # runner
    "run_reputation_league",
    "LeagueResult",
    # storage
    "write_league_outputs",
]
