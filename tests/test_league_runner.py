"""Tests for the league season runner."""

import json
from pathlib import Path

import pytest

from ultimatum_arena.agents import (
    HonestFairProposer,
    LyingGreedyProposer,
    ThresholdResponder,
)
from ultimatum_arena.league.agents import HeuristicParticipant, LLMParticipant
from ultimatum_arena.league.runner import run_reputation_league
from ultimatum_arena.league.schemas import (
    GossipConfig,
    LeagueAgentProfile,
    LeagueConfig,
)
from ultimatum_arena.league.storage import write_league_outputs
from ultimatum_arena.llm.client import FakeLLMClient


def _heuristic(agent_id: str, proposer, *, min_fraction: float = 0.25) -> HeuristicParticipant:
    profile = LeagueAgentProfile(agent_id=agent_id, display_name=agent_id, kind="heuristic")
    return HeuristicParticipant(profile, proposer, ThresholdResponder(min_fraction=min_fraction))


def _roster() -> list[HeuristicParticipant]:
    return [
        _heuristic("honest1", HonestFairProposer()),
        _heuristic("honest2", HonestFairProposer()),
        _heuristic("liar1", LyingGreedyProposer(claimed_fraction=0.6, offer_fraction=0.4)),
        _heuristic("liar2", LyingGreedyProposer(claimed_fraction=0.6, offer_fraction=0.4)),
    ]


class TestSeasonExecution:
    def test_runs_and_updates_payoffs(self) -> None:
        cfg = LeagueConfig(n_matches=20, matching_policy="random", audit_prob=0.5, rng_seed=1)
        result = run_reputation_league(_roster(), cfg)
        assert len(result.records) == 20
        assert result.failures == []
        total = sum(s.total_payoff for s in result.final_states)
        assert total == pytest.approx(result.summary["total_welfare"])

    def test_reputations_move_from_initial(self) -> None:
        cfg = LeagueConfig(n_matches=40, rng_seed=2, audit_prob=0.5)
        result = run_reputation_league(_roster(), cfg)
        reps = {s.profile.agent_id: s.public_reputation for s in result.final_states}
        # Honest agents should end with higher reputation than liars.
        assert min(reps["honest1"], reps["honest2"]) > max(reps["liar1"], reps["liar2"])

    def test_match_records_have_before_after_reputation(self) -> None:
        cfg = LeagueConfig(n_matches=10, rng_seed=3)
        result = run_reputation_league(_roster(), cfg)
        for rec in result.records:
            assert rec.proposer_reputation_before is not None
            assert rec.proposer_reputation_after is not None

    def test_deterministic_under_seed(self) -> None:
        cfg = LeagueConfig(n_matches=25, rng_seed=42, audit_prob=0.4)
        r1 = run_reputation_league(_roster(), cfg)
        r2 = run_reputation_league(_roster(), cfg)
        assert r1.summary["total_welfare"] == r2.summary["total_welfare"]
        assert [rec.match_id for rec in r1.records] == [rec.match_id for rec in r2.records]
        assert r1.summary["deception_rate"] == r2.summary["deception_rate"]

    def test_reputation_based_matching_runs(self) -> None:
        cfg = LeagueConfig(n_matches=20, matching_policy="reputation_based", rng_seed=5)
        result = run_reputation_league(_roster(), cfg)
        assert len(result.records) == 20

    def test_requires_two_participants(self) -> None:
        with pytest.raises(ValueError):
            run_reputation_league([_heuristic("solo", HonestFairProposer())], LeagueConfig(n_matches=5))

    def test_unique_ids_required(self) -> None:
        dup = [_heuristic("same", HonestFairProposer()), _heuristic("same", HonestFairProposer())]
        with pytest.raises(ValueError):
            run_reputation_league(dup, LeagueConfig(n_matches=5))


class TestGossipIntegration:
    def test_deterministic_gossip_published(self) -> None:
        cfg = LeagueConfig(n_matches=10, rng_seed=1, gossip=GossipConfig(mode="deterministic"))
        result = run_reputation_league(_roster(), cfg)
        # Two reviews per ok match.
        assert len(result.gossip_records) == 2 * len(result.records)

    def test_no_gossip_when_off(self) -> None:
        cfg = LeagueConfig(n_matches=10, rng_seed=1, gossip=GossipConfig(mode="off"))
        result = run_reputation_league(_roster(), cfg)
        assert result.gossip_records == []


class TestRefusalSafety:
    def test_llm_refusal_recorded_not_aborted(self) -> None:
        bad = FakeLLMClient(responses=["I will not deceive anyone."])
        roster = [
            LLMParticipant(LeagueAgentProfile(agent_id=f"x{i}", display_name=f"x{i}", kind="llm"), bad)
            for i in range(3)
        ]
        cfg = LeagueConfig(n_matches=6, rng_seed=1)
        result = run_reputation_league(roster, cfg)
        assert result.records == []
        assert len(result.failures) == 6
        assert all(f.status in ("proposer_refusal", "responder_refusal") for f in result.failures)
        assert result.summary == {}

    def test_mixed_valid_and_invalid(self) -> None:
        # Proposer returns valid JSON, responder accepts -> ok matches.
        good = FakeLLMClient(
            responses=['{"claimed_pie": 90, "offer": 35, "public_message": ""}', '{"accept": true}']
        )
        roster = [
            LLMParticipant(LeagueAgentProfile(agent_id=f"g{i}", display_name=f"g{i}", kind="llm"), good)
            for i in range(3)
        ]
        cfg = LeagueConfig(n_matches=5, rng_seed=1)
        result = run_reputation_league(roster, cfg)
        assert len(result.records) == 5


class TestStorageIntegration:
    def test_writes_expected_files(self, tmp_path: Path) -> None:
        cfg = LeagueConfig(n_matches=12, rng_seed=1, gossip=GossipConfig(mode="deterministic"))
        result = run_reputation_league(_roster(), cfg)
        out = write_league_outputs(
            tmp_path / "season",
            manifest={"experiment": "test"},
            records=result.records,
            failures=result.failures,
            final_states=result.final_states,
            gossip_records=result.gossip_records,
            reputation_history=result.reputation_history,
            summary=result.summary,
        )
        for name in [
            "manifest.json",
            "matches.jsonl",
            "final_agent_states.json",
            "public_reputation_history.csv",
            "gossip.jsonl",
            "league_summary.json",
            "leaderboard.csv",
        ]:
            assert (out / name).exists(), name
        # Records are valid JSONL.
        lines = (out / "matches.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 12
        assert json.loads(lines[0])["match_id"] == "m00000"
