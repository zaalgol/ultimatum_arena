"""Tests for match-making policies."""

import random

import pytest

from ultimatum_arena.league.matching import (
    VALID_MATCHING_POLICIES,
    build_schedule,
    select_pair,
)
from ultimatum_arena.league.schemas import LeagueAgentProfile, LeagueAgentState


def _states(reps: dict[str, float]) -> dict[str, LeagueAgentState]:
    return {
        aid: LeagueAgentState(
            profile=LeagueAgentProfile(agent_id=aid, display_name=aid),
            public_reputation=rep,
        )
        for aid, rep in reps.items()
    }


def _flat_states(ids: list[str]) -> dict[str, LeagueAgentState]:
    return _states({aid: 50.0 for aid in ids})


class TestRandomPolicy:
    def test_no_self_match(self) -> None:
        ids = [f"a{i}" for i in range(6)]
        states = _flat_states(ids)
        rng = random.Random(0)
        for _ in range(200):
            p, r = select_pair(ids, states, "random", rng)
            assert p != r

    def test_schedule_length(self) -> None:
        ids = [f"a{i}" for i in range(5)]
        schedule = build_schedule(ids, 30, "random", random.Random(1))
        assert len(schedule) == 30

    def test_seed_stable(self) -> None:
        ids = [f"a{i}" for i in range(5)]
        s1 = build_schedule(ids, 20, "random", random.Random(7))
        s2 = build_schedule(ids, 20, "random", random.Random(7))
        assert s1 == s2

    def test_different_seed_differs(self) -> None:
        ids = [f"a{i}" for i in range(5)]
        s1 = build_schedule(ids, 20, "random", random.Random(7))
        s2 = build_schedule(ids, 20, "random", random.Random(8))
        assert s1 != s2

    def test_covers_multiple_agents(self) -> None:
        ids = [f"a{i}" for i in range(6)]
        schedule = build_schedule(ids, 100, "random", random.Random(3))
        seen = {x for pair in schedule for x in pair}
        assert seen == set(ids)


class TestReputationPolicy:
    def test_no_self_match(self) -> None:
        states = _states({f"a{i}": float(i * 10) for i in range(6)})
        ids = list(states)
        rng = random.Random(0)
        for _ in range(200):
            p, r = select_pair(ids, states, "reputation_based", rng)
            assert p != r

    def test_seed_stable_static_states(self) -> None:
        states = _states({f"a{i}": float(i * 10) for i in range(6)})
        ids = list(states)
        s1 = build_schedule(ids, 20, "reputation_based", random.Random(5), states)
        s2 = build_schedule(ids, 20, "reputation_based", random.Random(5), states)
        assert s1 == s2

    def test_pairs_similar_reputation_more_than_random(self) -> None:
        # Two clusters: high (~90) and low (~10) reputation.
        high = {f"h{i}": 90.0 for i in range(4)}
        low = {f"l{i}": 10.0 for i in range(4)}
        states = _states({**high, **low})
        ids = list(states)

        def cluster(aid: str) -> str:
            return aid[0]

        def same_cluster_rate(policy: str, seed: int) -> float:
            schedule = build_schedule(ids, 400, policy, random.Random(seed), states)
            same = sum(1 for p, r in schedule if cluster(p) == cluster(r))
            return same / len(schedule)

        rep_rate = same_cluster_rate("reputation_based", 1)
        rand_rate = same_cluster_rate("random", 1)
        # Reputation-based pairing should cluster like-reputation agents together
        # more often than uniform random.
        assert rep_rate > rand_rate


class TestValidation:
    def test_unknown_policy_raises(self) -> None:
        with pytest.raises(ValueError):
            select_pair(["a", "b"], _flat_states(["a", "b"]), "bogus", random.Random(0))

    def test_too_few_agents_raises(self) -> None:
        with pytest.raises(ValueError):
            select_pair(["a"], _flat_states(["a"]), "random", random.Random(0))

    def test_reputation_schedule_requires_states(self) -> None:
        with pytest.raises(ValueError):
            build_schedule(["a", "b"], 5, "reputation_based", random.Random(0))

    def test_policy_set_exported(self) -> None:
        assert VALID_MATCHING_POLICIES == {"random", "reputation_based"}
