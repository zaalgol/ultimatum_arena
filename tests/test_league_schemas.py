"""Tests for league Pydantic schemas: serialization round-trips and defaults."""

import pytest

from ultimatum_arena.league.schemas import (
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


def _profile() -> LeagueAgentProfile:
    return LeagueAgentProfile(agent_id="a1", display_name="Alice", kind="llm", proposer_strategy="honest_fair")


class TestProfileAndState:
    def test_profile_round_trip(self) -> None:
        p = _profile()
        assert LeagueAgentProfile.model_validate_json(p.model_dump_json()) == p

    def test_state_defaults(self) -> None:
        s = LeagueAgentState(profile=_profile())
        assert s.total_payoff == 0.0
        assert s.public_reputation == 50.0
        assert s.matches_played == 0

    def test_state_round_trip(self) -> None:
        s = LeagueAgentState(profile=_profile(), total_payoff=12.5, public_reputation=70.0)
        restored = LeagueAgentState.model_validate_json(s.model_dump_json())
        assert restored == s


class TestMatchRecord:
    def test_round_trip(self) -> None:
        rec = LeagueMatchRecord(
            match_id="m0",
            season_index=0,
            proposer_id="a1",
            responder_id="a2",
            true_pie=100.0,
            claimed_pie=80.0,
            offer=30.0,
            accepted=True,
            audit_occurred=False,
            lie_detected=False,
            proposer_payoff=70.0,
            responder_payoff=30.0,
            proposer_reputation_before=50.0,
            responder_reputation_before=50.0,
            proposer_reputation_after=55.0,
            responder_reputation_after=50.0,
        )
        assert LeagueMatchRecord.model_validate_json(rec.model_dump_json()) == rec
        assert rec.status == "ok"


class TestMemoryAndGossipSchemas:
    def test_memory_entry_optionals_default_none(self) -> None:
        e = PrivateMemoryEntry(
            observer_id="a1",
            target_id="a2",
            match_id="m0",
            season_index=0,
            target_role="proposer",
            accepted=True,
        )
        assert e.target_offer_ratio_true is None
        assert e.target_claimed_truthfully is None

    def test_gossip_record_round_trip(self) -> None:
        g = GossipRecord(
            review_id="r0", match_id="m0", season_index=0, author_id="a1",
            target_id="a2", target_role="proposer", text="fair", rating=0.5, created_at_match=0,
        )
        assert GossipRecord.model_validate_json(g.model_dump_json()) == g


class TestConfigs:
    def test_reputation_config_defaults(self) -> None:
        c = ReputationConfig()
        assert c.initial == 50.0
        assert c.use_ground_truth is True
        assert c.score_responders is False

    def test_alpha_bounds_validated(self) -> None:
        with pytest.raises(ValueError):
            ReputationConfig(alpha=1.5)

    def test_league_config_requires_positive_matches(self) -> None:
        with pytest.raises(ValueError):
            LeagueConfig(n_matches=0)

    def test_league_config_nested_defaults(self) -> None:
        cfg = LeagueConfig(n_matches=10)
        assert isinstance(cfg.reputation, ReputationConfig)
        assert isinstance(cfg.memory, MemoryConfig)
        assert isinstance(cfg.gossip, GossipConfig)
        assert cfg.matching_policy == "random"


class TestEnumValidation:
    """P2-3: invalid enums must be rejected at the schema boundary, not silently coerced."""

    def test_invalid_gossip_mode_rejected(self) -> None:
        with pytest.raises(ValueError):
            GossipConfig(mode="deterministicc")

    def test_valid_gossip_modes_accepted(self) -> None:
        for mode in ("off", "deterministic", "llm"):
            assert GossipConfig(mode=mode).mode == mode

    def test_invalid_matching_policy_rejected(self) -> None:
        with pytest.raises(ValueError):
            LeagueConfig(n_matches=5, matching_policy="elo")

    def test_valid_matching_policies_accepted(self) -> None:
        for policy in ("random", "reputation_based"):
            assert LeagueConfig(n_matches=5, matching_policy=policy).matching_policy == policy

    def test_gossip_rating_bounds_enforced(self) -> None:
        with pytest.raises(ValueError):
            GossipRecord(
                review_id="r", match_id="m", season_index=0, author_id="a",
                target_id="b", target_role="proposer", text="x", rating=5.0, created_at_match=0,
            )

    def test_gossip_rating_none_allowed(self) -> None:
        g = GossipRecord(
            review_id="r", match_id="m", season_index=0, author_id="a",
            target_id="b", target_role="proposer", text="x", rating=None, created_at_match=0,
        )
        assert g.rating is None
