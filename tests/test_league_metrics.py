"""Tests for compute_league_metrics (pure season-level metrics)."""

import pytest

from ultimatum_arena.league.metrics import compute_league_metrics
from ultimatum_arena.league.schemas import (
    GossipRecord,
    LeagueAgentProfile,
    LeagueAgentState,
    LeagueMatchRecord,
)


def _state(aid: str, payoff: float, rep: float, *, as_proposer: int = 1, accepted: int = 1) -> LeagueAgentState:
    return LeagueAgentState(
        profile=LeagueAgentProfile(agent_id=aid, display_name=aid),
        total_payoff=payoff,
        public_reputation=rep,
        matches_as_proposer=as_proposer,
        accepted_matches=accepted,
        matches_played=as_proposer,
    )


def _record(
    *,
    match_id: str = "m",
    proposer_id: str = "p",
    responder_id: str = "r",
    true_pie: float = 100.0,
    claimed_pie: float = 100.0,
    offer: float = 40.0,
    accepted: bool = True,
    lie_detected: bool = False,
    prop_rep_before: float = 50.0,
) -> LeagueMatchRecord:
    return LeagueMatchRecord(
        match_id=match_id,
        season_index=0,
        proposer_id=proposer_id,
        responder_id=responder_id,
        true_pie=true_pie,
        claimed_pie=claimed_pie,
        offer=offer,
        accepted=accepted,
        audit_occurred=lie_detected,
        lie_detected=lie_detected,
        proposer_payoff=true_pie - offer,
        responder_payoff=offer,
        proposer_reputation_before=prop_rep_before,
        responder_reputation_before=50.0,
        proposer_reputation_after=prop_rep_before,
        responder_reputation_after=50.0,
    )


class TestComputeLeagueMetrics:
    def test_empty_returns_empty(self) -> None:
        assert compute_league_metrics([], []) == {}

    def test_basic_counts(self) -> None:
        records = [_record(match_id=f"m{i}") for i in range(4)]
        states = [_state("p", 240.0, 60.0), _state("r", 160.0, 50.0)]
        m = compute_league_metrics(records, states)
        assert m["n_matches"] == 4
        assert m["n_agents"] == 2
        assert m["acceptance_rate"] == pytest.approx(1.0)
        assert m["total_welfare"] == pytest.approx(400.0)

    def test_deception_and_detection_rates(self) -> None:
        records = [
            _record(match_id="m0", claimed_pie=60.0, true_pie=100.0, lie_detected=True),
            _record(match_id="m1", claimed_pie=100.0, true_pie=100.0),
        ]
        states = [_state("p", 100.0, 40.0), _state("r", 80.0, 50.0)]
        m = compute_league_metrics(records, states)
        assert m["deception_rate"] == pytest.approx(0.5)
        assert m["detected_lie_rate"] == pytest.approx(0.5)

    def test_reputation_payoff_correlation_positive(self) -> None:
        records = [_record(match_id=f"m{i}") for i in range(3)]
        states = [
            _state("a", 100.0, 30.0),
            _state("b", 200.0, 60.0),
            _state("c", 300.0, 90.0),
        ]
        m = compute_league_metrics(records, states)
        assert m["reputation_payoff_correlation"] > 0.99

    def test_leaderboard_sorted_by_payoff(self) -> None:
        records = [_record()]
        states = [_state("a", 100.0, 50.0), _state("b", 300.0, 50.0), _state("c", 200.0, 50.0)]
        m = compute_league_metrics(records, states)
        ranks = [row["agent_id"] for row in m["leaderboard"]]
        assert ranks == ["b", "c", "a"]

    def test_gini_bounds(self) -> None:
        records = [_record()]
        states = [_state("a", 0.0, 50.0), _state("b", 100.0, 50.0)]
        m = compute_league_metrics(records, states)
        assert 0.0 <= m["payoff_gini"] <= 1.0

    def test_deception_segments(self) -> None:
        records = (
            [_record(match_id=f"a{i}", claimed_pie=60.0, true_pie=100.0) for i in range(4)]
            + [_record(match_id=f"b{i}", claimed_pie=100.0, true_pie=100.0) for i in range(4)]
        )
        states = [_state("p", 100.0, 50.0), _state("r", 50.0, 50.0)]
        m = compute_league_metrics(records, states)
        assert m["deception_rate_first_half"] > m["deception_rate_second_half"]

    def test_gossip_metrics_included(self) -> None:
        records = [_record()]
        states = [_state("p", 100.0, 80.0), _state("r", 40.0, 20.0)]
        gossip = [
            GossipRecord(review_id="g0", match_id="m", season_index=0, author_id="r",
                         target_id="p", target_role="proposer", text="good", rating=0.8, created_at_match=0),
        ]
        m = compute_league_metrics(records, states, gossip)
        assert m["gossip_review_count"] == 1
        assert m["gossip_mean_rating"] == pytest.approx(0.8)
