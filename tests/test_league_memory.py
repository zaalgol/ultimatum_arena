"""Tests for private memory: relevance, capping, and public-information regime."""

from ultimatum_arena.league.memory import PrivateMemoryStore, build_memory_entry
from ultimatum_arena.league.schemas import LeagueMatchRecord, MemoryConfig


def _record(
    *,
    match_id: str = "m0",
    season_index: int = 0,
    proposer_id: str = "p",
    responder_id: str = "r",
    true_pie: float = 100.0,
    claimed_pie: float = 100.0,
    offer: float = 40.0,
    accepted: bool = True,
    audit_occurred: bool = False,
    lie_detected: bool = False,
    public_message: str = "",
) -> LeagueMatchRecord:
    return LeagueMatchRecord(
        match_id=match_id,
        season_index=season_index,
        proposer_id=proposer_id,
        responder_id=responder_id,
        true_pie=true_pie,
        claimed_pie=claimed_pie,
        offer=offer,
        public_message=public_message,
        accepted=accepted,
        audit_occurred=audit_occurred,
        lie_detected=lie_detected,
        proposer_payoff=true_pie - offer,
        responder_payoff=offer,
        proposer_reputation_before=50.0,
        responder_reputation_before=50.0,
        proposer_reputation_after=50.0,
        responder_reputation_after=50.0,
    )


class TestMemoryEntryInformationRegime:
    def test_unaudited_proposer_truth_unknown(self) -> None:
        entry = build_memory_entry(
            observer_id="r", target_id="p", target_name="P", target_role="proposer",
            record=_record(claimed_pie=60.0, true_pie=100.0, audit_occurred=False),
        )
        assert entry.target_claimed_truthfully is None
        assert entry.target_offer_ratio_true is None
        assert "true pie unknown" in entry.summary

    def test_audited_lie_revealed(self) -> None:
        entry = build_memory_entry(
            observer_id="r", target_id="p", target_name="P", target_role="proposer",
            record=_record(claimed_pie=60.0, true_pie=100.0, audit_occurred=True, lie_detected=True),
        )
        assert entry.target_claimed_truthfully is False
        assert entry.target_offer_ratio_true is not None
        assert "caught by audit" in entry.summary

    def test_audited_truthful(self) -> None:
        entry = build_memory_entry(
            observer_id="r", target_id="p", target_name="P", target_role="proposer",
            record=_record(claimed_pie=100.0, true_pie=100.0, audit_occurred=True, lie_detected=False),
        )
        assert entry.target_claimed_truthfully is True

    def test_responder_target_summary(self) -> None:
        entry = build_memory_entry(
            observer_id="p", target_id="r", target_name="R", target_role="responder",
            record=_record(accepted=False, offer=10.0),
        )
        assert entry.target_role == "responder"
        assert "rejected" in entry.summary


class TestPrivateMemoryStore:
    def test_only_relevant_opponent_returned(self) -> None:
        store = PrivateMemoryStore(MemoryConfig(per_opponent_limit=5))
        store.record_match(_record(proposer_id="p", responder_id="r"), proposer_name="P", responder_name="R")
        store.record_match(
            _record(match_id="m1", proposer_id="p", responder_id="x"), proposer_name="P", responder_name="X"
        )
        # Observer p remembers r and x separately.
        assert len(store.recent_about("p", "r")) == 1
        assert len(store.recent_about("p", "x")) == 1
        # No cross-talk: p has no memory of an unseen opponent.
        assert store.recent_about("p", "z") == []

    def test_capped_per_opponent(self) -> None:
        store = PrivateMemoryStore(MemoryConfig(per_opponent_limit=2))
        for i in range(5):
            store.record_match(
                _record(match_id=f"m{i}", proposer_id="p", responder_id="r"),
                proposer_name="P", responder_name="R",
            )
        entries = store.recent_about("p", "r")
        assert len(entries) == 2
        # Keeps the most recent.
        assert entries[-1].match_id == "m4"

    def test_disabled_memory_stores_nothing(self) -> None:
        store = PrivateMemoryStore(MemoryConfig(enabled=False))
        store.record_match(_record(), proposer_name="P", responder_name="R")
        assert store.recent_about("p", "r") == []

    def test_deterministic_summaries(self) -> None:
        store1 = PrivateMemoryStore(MemoryConfig())
        store2 = PrivateMemoryStore(MemoryConfig())
        rec = _record(claimed_pie=80.0, offer=30.0)
        store1.record_match(rec, proposer_name="P", responder_name="R")
        store2.record_match(rec, proposer_name="P", responder_name="R")
        assert store1.recent_about("r", "p")[0].summary == store2.recent_about("r", "p")[0].summary
