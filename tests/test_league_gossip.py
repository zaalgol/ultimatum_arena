"""Tests for deterministic and LLM gossip generation and the gossip store."""

from ultimatum_arena.league.gossip import (
    GossipStore,
    deterministic_review,
    llm_review,
)
from ultimatum_arena.league.schemas import LeagueMatchRecord
from ultimatum_arena.llm.client import FakeLLMClient


def _record(
    *,
    match_id: str = "m0",
    offer: float = 40.0,
    claimed_pie: float = 100.0,
    true_pie: float = 100.0,
    accepted: bool = True,
    audit_occurred: bool = False,
    lie_detected: bool = False,
) -> LeagueMatchRecord:
    return LeagueMatchRecord(
        match_id=match_id,
        season_index=0,
        proposer_id="p",
        responder_id="r",
        true_pie=true_pie,
        claimed_pie=claimed_pie,
        offer=offer,
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


def _review(record, role="proposer"):
    return deterministic_review(
        record=record, author_id="r", target_id="p", target_name="P", target_role=role
    )


class TestDeterministicReview:
    def test_generous_offer_positive(self) -> None:
        g = _review(_record(offer=50.0))
        assert g.rating > 0

    def test_lowball_negative(self) -> None:
        g = _review(_record(offer=10.0))
        assert g.rating < 0

    def test_detected_lie_strongly_negative(self) -> None:
        g = _review(_record(offer=40.0, claimed_pie=60.0, true_pie=100.0, audit_occurred=True, lie_detected=True))
        assert g.rating <= -0.5
        assert "lying" in g.text

    def test_rating_bounded(self) -> None:
        assert -1.0 <= _review(_record(offer=0.0, lie_detected=True)).rating <= 1.0
        assert -1.0 <= _review(_record(offer=100.0)).rating <= 1.0

    def test_does_not_expose_true_pie(self) -> None:
        # An unaudited deceptive match must not leak true_pie in public gossip.
        g = _review(_record(offer=40.0, claimed_pie=60.0, true_pie=100.0, audit_occurred=False))
        assert "100" not in g.text

    def test_deterministic(self) -> None:
        rec = _record(offer=33.0)
        assert _review(rec).text == _review(rec).text
        assert _review(rec).rating == _review(rec).rating


class TestLLMReview:
    def test_uses_model_output(self) -> None:
        client = FakeLLMClient(responses=['{"text": "Great player", "rating": 0.9}'])
        g = llm_review(client, record=_record(), author_id="r", target_id="p", target_name="P", target_role="proposer")
        assert g.text == "Great player"
        assert g.rating == 0.9

    def test_falls_back_on_bad_output(self) -> None:
        client = FakeLLMClient(responses=["I refuse to gossip."])
        g = llm_review(client, record=_record(offer=50.0), author_id="r", target_id="p", target_name="P", target_role="proposer")
        # Falls back to the deterministic review rather than raising.
        assert g.rating is not None
        assert g.text

    def test_rating_clamped(self) -> None:
        client = FakeLLMClient(responses=['{"text": "x", "rating": 5.0}'])
        g = llm_review(client, record=_record(), author_id="r", target_id="p", target_name="P", target_role="proposer")
        assert g.rating == 1.0


class TestGossipStore:
    def test_recent_about_caps(self) -> None:
        store = GossipStore()
        for i in range(5):
            store.add(_review(_record(match_id=f"m{i}", offer=40.0)))
        assert len(store.recent_about("p", 3)) == 3

    def test_recent_about_filters_target(self) -> None:
        store = GossipStore()
        store.add(deterministic_review(record=_record(), author_id="r", target_id="p", target_name="P", target_role="proposer"))
        store.add(deterministic_review(record=_record(), author_id="p", target_id="r", target_name="R", target_role="responder"))
        assert all(g.target_id == "p" for g in store.recent_about("p", 5))

    def test_zero_k_returns_empty(self) -> None:
        store = GossipStore()
        store.add(_review(_record()))
        assert store.recent_about("p", 0) == []
