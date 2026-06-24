"""Season runner for the Reputation Network League.

``run_reputation_league`` plays ``config.n_matches`` one-shot Hidden Pie Audit
matches across a population of :class:`LeagueParticipant` objects. Each match:

1. selects a (proposer, responder) pair via the matching policy,
2. builds league social context for each role (opponent reputation, the
   observer's private memory, recent public gossip, leaderboard summary),
3. runs the proposer then responder action (refusal-safe),
4. resolves the Hidden Pie Audit round and updates payoffs + reputation,
5. updates both agents' private memory, optionally publishes gossip,
6. records an auditable :class:`LeagueMatchRecord` with before/after reputations.

Refusal-safety: if an LLM participant refuses or returns unparseable JSON, the
match is recorded as a failure (status ``proposer_refusal`` / ``responder_refusal``)
and the season continues; no payoff/reputation/memory updates happen for a failed
match. This mirrors the existing deception-probe pattern.

The runner is synchronous and deterministic under ``config.rng_seed``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Sequence

from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
from ultimatum_arena.league.agents import LeagueParticipant
from ultimatum_arena.league.gossip import GossipStore, deterministic_review, llm_review
from ultimatum_arena.league.matching import select_pair
from ultimatum_arena.league.memory import PrivateMemoryStore
from ultimatum_arena.league.metrics import compute_league_metrics
from ultimatum_arena.league.prompts import LeagueContext
from ultimatum_arena.league.reputation import apply_match_to_state
from ultimatum_arena.league.schemas import (
    GossipRecord,
    LeagueAgentState,
    LeagueConfig,
    LeagueMatchRecord,
)
from ultimatum_arena.llm.client import LLMClient
from ultimatum_arena.llm.errors import LLMParseError


@dataclass
class LeagueResult:
    """Everything produced by one season."""

    records: list[LeagueMatchRecord] = field(default_factory=list)
    failures: list[LeagueMatchRecord] = field(default_factory=list)
    final_states: list[LeagueAgentState] = field(default_factory=list)
    gossip_records: list[GossipRecord] = field(default_factory=list)
    reputation_history: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _leaderboard_summary(states: dict[str, LeagueAgentState], top: int = 3) -> str:
    ordered = sorted(states.values(), key=lambda s: s.total_payoff, reverse=True)
    parts = [
        f"{s.profile.display_name} ({s.total_payoff:.0f} pts, rep {s.public_reputation:.0f})"
        for s in ordered[:top]
    ]
    return "; ".join(parts)


def _build_context(
    *,
    observer_id: str,
    opponent_id: str,
    opponent_name: str,
    memory: PrivateMemoryStore,
    gossip_store: GossipStore,
    states: dict[str, LeagueAgentState],
    config: LeagueConfig,
) -> LeagueContext:
    summaries = [
        e.summary for e in memory.recent_about(observer_id, opponent_id)
    ]
    gossip = (
        gossip_store.recent_about(opponent_id, config.gossip.visible_k)
        if config.gossip.mode != "off"
        else []
    )
    return LeagueContext(
        opponent_name=opponent_name,
        opponent_reputation=states[opponent_id].public_reputation,
        memory_summaries=summaries,
        gossip=gossip,
        leaderboard_summary=_leaderboard_summary(states),
    )


def run_reputation_league(
    participants: Sequence[LeagueParticipant],
    config: LeagueConfig,
    *,
    gossip_client: LLMClient | None = None,
) -> LeagueResult:
    """Run one season and return a :class:`LeagueResult` (no file writing here)."""
    if len(participants) < 2:
        raise ValueError("A league needs at least two participants.")

    by_id: dict[str, LeagueParticipant] = {p.agent_id: p for p in participants}
    if len(by_id) != len(participants):
        raise ValueError("Participant agent_ids must be unique.")

    agent_ids = list(by_id.keys())
    states: dict[str, LeagueAgentState] = {
        p.agent_id: LeagueAgentState(
            profile=p.profile, public_reputation=config.reputation.initial
        )
        for p in participants
    }

    rng = random.Random(config.rng_seed)
    memory = PrivateMemoryStore(config.memory)
    gossip_store = GossipStore()

    result = LeagueResult(final_states=list(states.values()))

    for match_index in range(config.n_matches):
        proposer_id, responder_id = select_pair(
            agent_ids, states, config.matching_policy, rng
        )
        proposer = by_id[proposer_id]
        responder = by_id[responder_id]
        match_id = f"m{match_index:05d}"

        # Fresh env per match keeps true_pie/audit independent & seedable.
        match_seed = rng.randrange(1 << 31)
        env = HiddenPieAuditEnv(
            pie_range=config.pie_range,
            audit_prob=config.audit_prob,
            lie_penalty=config.lie_penalty,
            rng_seed=match_seed,
        )

        prop_rep_before = states[proposer_id].public_reputation
        resp_rep_before = states[responder_id].public_reputation

        true_pie, prop_obs = env.proposer_observation()

        prop_context = _build_context(
            observer_id=proposer_id,
            opponent_id=responder_id,
            opponent_name=responder.profile.display_name,
            memory=memory,
            gossip_store=gossip_store,
            states=states,
            config=config,
        )

        try:
            prop_action = proposer.propose(prop_obs, prop_context)
        except LLMParseError as exc:
            result.failures.append(
                _failure_record(
                    match_id, match_index, proposer_id, responder_id, true_pie,
                    prop_rep_before, resp_rep_before, "proposer_refusal", exc,
                    getattr(proposer, "last_raw_response", ""),
                )
            )
            continue

        resp_obs = env.responder_observation(prop_action)
        resp_context = _build_context(
            observer_id=responder_id,
            opponent_id=proposer_id,
            opponent_name=proposer.profile.display_name,
            memory=memory,
            gossip_store=gossip_store,
            states=states,
            config=config,
        )

        try:
            resp_action = responder.respond(resp_obs, resp_context)
        except LLMParseError as exc:
            result.failures.append(
                _failure_record(
                    match_id, match_index, proposer_id, responder_id, true_pie,
                    prop_rep_before, resp_rep_before, "responder_refusal", exc,
                    getattr(responder, "last_raw_response", ""),
                )
            )
            continue

        round_result = env.step(true_pie, prop_action, resp_action)

        # Update state (payoffs, reputation, behaviour counters).
        apply_match_to_state(states[proposer_id], round_result, "proposer", config.reputation)
        apply_match_to_state(states[responder_id], round_result, "responder", config.reputation)

        record = LeagueMatchRecord(
            match_id=match_id,
            season_index=match_index,
            proposer_id=proposer_id,
            responder_id=responder_id,
            true_pie=round_result.true_pie,
            claimed_pie=round_result.claimed_pie,
            offer=round_result.offer,
            public_message=round_result.public_message,
            accepted=round_result.accepted,
            audit_occurred=round_result.audit_occurred,
            lie_detected=round_result.lie_detected,
            proposer_payoff=round_result.proposer_payoff,
            responder_payoff=round_result.responder_payoff,
            proposer_reputation_before=prop_rep_before,
            responder_reputation_before=resp_rep_before,
            proposer_reputation_after=states[proposer_id].public_reputation,
            responder_reputation_after=states[responder_id].public_reputation,
            status="ok",
        )
        result.records.append(record)

        # Private memory for both agents.
        memory.record_match(
            record,
            proposer_name=proposer.profile.display_name,
            responder_name=responder.profile.display_name,
        )

        # Optional gossip publication.
        if config.gossip.mode != "off":
            _publish_gossip(
                gossip_store, record, by_id, config, gossip_client, result
            )

        # Reputation history snapshots (one row per updated agent).
        result.reputation_history.append(
            {
                "match_index": match_index,
                "match_id": match_id,
                "agent_id": proposer_id,
                "role": "proposer",
                "reputation_after": states[proposer_id].public_reputation,
            }
        )
        result.reputation_history.append(
            {
                "match_index": match_index,
                "match_id": match_id,
                "agent_id": responder_id,
                "role": "responder",
                "reputation_after": states[responder_id].public_reputation,
            }
        )

    result.final_states = list(states.values())
    result.gossip_records = gossip_store.records
    result.summary = compute_league_metrics(
        result.records, result.final_states, result.gossip_records or None
    )
    return result


def _publish_gossip(
    gossip_store: GossipStore,
    record: LeagueMatchRecord,
    by_id: dict[str, LeagueParticipant],
    config: LeagueConfig,
    gossip_client: LLMClient | None,
    result: LeagueResult,
) -> None:
    """Each participant publishes one review about the opponent (refusal-safe)."""
    use_llm = config.gossip.mode == "llm" and gossip_client is not None
    pairs = [
        (record.proposer_id, record.responder_id, "responder"),  # proposer reviews responder
        (record.responder_id, record.proposer_id, "proposer"),  # responder reviews proposer
    ]
    for author_id, target_id, target_role in pairs:
        target_name = by_id[target_id].profile.display_name
        if use_llm:
            review = llm_review(
                gossip_client,
                record=record,
                author_id=author_id,
                target_id=target_id,
                target_name=target_name,
                target_role=target_role,
            )
        else:
            review = deterministic_review(
                record=record,
                author_id=author_id,
                target_id=target_id,
                target_name=target_name,
                target_role=target_role,
            )
        gossip_store.add(review)


def _failure_record(
    match_id: str,
    match_index: int,
    proposer_id: str,
    responder_id: str,
    true_pie: float,
    prop_rep_before: float,
    resp_rep_before: float,
    status: str,
    exc: Exception,
    raw_response: str,
) -> LeagueMatchRecord:
    """Build a record for a refused/unparseable match (no state updates)."""
    return LeagueMatchRecord(
        match_id=match_id,
        season_index=match_index,
        proposer_id=proposer_id,
        responder_id=responder_id,
        true_pie=true_pie,
        claimed_pie=0.0,
        offer=0.0,
        public_message="",
        accepted=False,
        audit_occurred=False,
        lie_detected=False,
        proposer_payoff=0.0,
        responder_payoff=0.0,
        proposer_reputation_before=prop_rep_before,
        responder_reputation_before=resp_rep_before,
        proposer_reputation_after=prop_rep_before,
        responder_reputation_after=resp_rep_before,
        status=status,
        metadata={
            "error": str(exc)[:200],
            "raw_response": (raw_response or "")[:600],
        },
    )
