"""Match-making policies for the league.

Two policies are implemented:

* ``random`` — uniformly pick two distinct agents, then randomly assign roles.
* ``reputation_based`` — pick an anchor agent, then pick the opponent with
  probability weighted toward similar public reputation (close-rep pairings are
  more likely). Roles are still randomised.

Both policies are deterministic under a seeded :class:`random.Random` and never
produce a self-match. ``reputation_based`` reads live agent states, so it must be
called per match (reputations evolve during a season).
"""

from __future__ import annotations

import random
from typing import Mapping

from ultimatum_arena.league.schemas import VALID_MATCHING_POLICIES, LeagueAgentState

__all__ = ["VALID_MATCHING_POLICIES", "select_pair", "build_schedule"]


def _assign_roles(a: str, b: str, rng: random.Random) -> tuple[str, str]:
    """Randomly order two agent ids into (proposer_id, responder_id)."""
    if rng.random() < 0.5:
        return a, b
    return b, a


def _select_random(agent_ids: list[str], rng: random.Random) -> tuple[str, str]:
    a, b = rng.sample(agent_ids, 2)
    return _assign_roles(a, b, rng)


def _select_reputation_based(
    agent_ids: list[str],
    states: Mapping[str, LeagueAgentState],
    rng: random.Random,
) -> tuple[str, str]:
    """Pick an anchor uniformly, then an opponent weighted toward similar rep."""
    anchor = rng.choice(agent_ids)
    others = [aid for aid in agent_ids if aid != anchor]
    anchor_rep = states[anchor].public_reputation
    # Weight inversely with reputation distance: closer reputations pair more
    # often. The +1 avoids division by zero and bounds the maximum weight.
    weights = [1.0 / (1.0 + abs(anchor_rep - states[aid].public_reputation)) for aid in others]
    opponent = rng.choices(others, weights=weights, k=1)[0]
    return _assign_roles(anchor, opponent, rng)


def select_pair(
    agent_ids: list[str],
    states: Mapping[str, LeagueAgentState],
    policy: str,
    rng: random.Random,
) -> tuple[str, str]:
    """Return a single ``(proposer_id, responder_id)`` pair for one match.

    Raises ``ValueError`` for an unknown policy or fewer than two agents.
    """
    if policy not in VALID_MATCHING_POLICIES:
        raise ValueError(
            f"Unknown matching policy {policy!r}. Valid: {sorted(VALID_MATCHING_POLICIES)}"
        )
    if len(agent_ids) < 2:
        raise ValueError("Need at least two agents to form a match.")

    if policy == "random":
        return _select_random(agent_ids, rng)
    return _select_reputation_based(agent_ids, states, rng)


def build_schedule(
    agent_ids: list[str],
    n_matches: int,
    policy: str,
    rng: random.Random,
    states: Mapping[str, LeagueAgentState] | None = None,
) -> list[tuple[str, str]]:
    """Return a full ``n_matches``-long schedule of pairs.

    Convenience for tests and the ``random`` policy. ``states`` is required for
    ``reputation_based``; note this builds the schedule against the *static*
    states passed in (the runner instead calls :func:`select_pair` per match so
    reputation-based pairing reacts to evolving reputations).
    """
    if policy == "reputation_based" and states is None:
        raise ValueError("reputation_based scheduling requires agent states.")
    states = states or {}
    return [select_pair(agent_ids, states, policy, rng) for _ in range(n_matches)]
