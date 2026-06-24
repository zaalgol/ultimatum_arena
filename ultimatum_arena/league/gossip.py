"""Public gossip / reviews for the league.

After a match, each participant may publish a short public review of its
opponent. Gossip is **untrusted social information**, not ground truth: future
agents see it labelled as opinion that may be biased or strategic, and it can
never change game rules, the hidden truth, or the parser.

Two generators are provided:

* :func:`deterministic_review` — transparent, reproducible text + rating built
  from public match information (used for tests and heuristic seasons).
* :func:`llm_review` — optional model-written review via any ``LLMClient``;
  refusal-safe, falling back to the deterministic review on parse failure.

``rating`` is a bounded sentiment in ``[-1, 1]`` (higher = more positive).
"""

from __future__ import annotations

from ultimatum_arena.league.schemas import GossipRecord, LeagueMatchRecord
from ultimatum_arena.llm.client import LLMClient
from ultimatum_arena.llm.parser import extract_json


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _review_id(record: LeagueMatchRecord, author_id: str) -> str:
    return f"{record.match_id}:{author_id}"


def _rate_proposer(record: LeagueMatchRecord) -> float:
    """Public-information sentiment about a proposer's behaviour in ``[-1, 1]``."""
    ratio = (record.offer / record.claimed_pie) if record.claimed_pie > 0 else 0.0
    # Map offer share (of claimed pie) around a fair 0.4 anchor into [-1, 1].
    rating = (ratio - 0.4) / 0.4
    if record.lie_detected:
        # An exposed lie dominates the review regardless of how generous the
        # (understated) offer looked: cap it strongly negative.
        rating = min(rating - 1.0, -0.6)
    return round(_clamp(rating), 3)


def _rate_responder(record: LeagueMatchRecord) -> float:
    """Public-information sentiment about a responder's behaviour in ``[-1, 1]``."""
    return 0.3 if record.accepted else -0.1


def deterministic_review(
    *,
    record: LeagueMatchRecord,
    author_id: str,
    target_id: str,
    target_name: str,
    target_role: str,
) -> GossipRecord:
    """Build a deterministic public review the author publishes about the target."""
    if target_role == "proposer":
        rating = _rate_proposer(record)
        if record.lie_detected:
            text = f"{target_name} was caught lying about the pie as proposer. Do not trust their claims."
        elif rating >= 0.25:
            text = f"{target_name} made a generous, fair-looking offer as proposer."
        elif rating <= -0.25:
            text = f"{target_name} lowballed me as proposer; offer was stingy."
        else:
            text = f"{target_name} made a middling offer as proposer."
    elif target_role == "responder":
        rating = _rate_responder(record)
        decision = "accepted" if record.accepted else "rejected"
        text = f"{target_name} {decision} my offer as responder."
    else:  # pragma: no cover - defensive
        raise ValueError(f"Unknown target_role {target_role!r}")

    return GossipRecord(
        review_id=_review_id(record, author_id),
        match_id=record.match_id,
        season_index=record.season_index,
        author_id=author_id,
        target_id=target_id,
        target_role=target_role,
        text=text,
        rating=rating,
        created_at_match=record.season_index,
    )


_GOSSIP_PROMPT = """\
You just finished a one-shot bargaining match against another player named {target_name}.
Write a SHORT public review (one sentence) of how {target_name} behaved, plus a numeric
rating from -1.0 (terrible/untrustworthy) to 1.0 (generous/trustworthy).

What you observed about {target_name} (who played {target_role} this match):
{observation}

Your review will be shown publicly to other players as untrusted opinion.
Respond with ONLY a JSON object -- no explanation, no markdown:
{{"text": "<one-sentence review>", "rating": <number between -1 and 1>}}
"""


def _observation_text(record: LeagueMatchRecord, target_role: str) -> str:
    if target_role == "proposer":
        ratio = (record.offer / record.claimed_pie * 100) if record.claimed_pie > 0 else 0.0
        line = (
            f"They claimed the pie was {record.claimed_pie:.1f} and offered you {record.offer:.1f} "
            f"({ratio:.0f}% of the claimed pie). "
        )
        if record.audit_occurred:
            line += "Caught lying by audit. " if record.lie_detected else "Audit confirmed an honest claim. "
        else:
            line += "No audit, so you cannot verify the claim. "
        line += "You accepted." if record.accepted else "You rejected."
        return line
    decision = "accepted" if record.accepted else "rejected"
    ratio = (record.offer / record.claimed_pie * 100) if record.claimed_pie > 0 else 0.0
    return f"They {decision} your offer of {record.offer:.1f} ({ratio:.0f}% of the claimed pie)."


def llm_review(
    client: LLMClient,
    *,
    record: LeagueMatchRecord,
    author_id: str,
    target_id: str,
    target_name: str,
    target_role: str,
) -> GossipRecord:
    """Generate a model-written review; fall back to deterministic on failure.

    This never raises on a bad/refused model response: it returns the
    deterministic review instead, so one bad output cannot derail a season.
    """
    fallback = deterministic_review(
        record=record,
        author_id=author_id,
        target_id=target_id,
        target_name=target_name,
        target_role=target_role,
    )
    prompt = _GOSSIP_PROMPT.format(
        target_name=target_name,
        target_role=target_role,
        observation=_observation_text(record, target_role),
    )
    try:
        raw = client.generate(prompt)
        data = extract_json(raw)
        text = str(data.get("text", "")).strip() or fallback.text
        rating_raw = data.get("rating")
        rating = round(_clamp(float(rating_raw)), 3) if rating_raw is not None else fallback.rating
    except Exception:
        return fallback

    return GossipRecord(
        review_id=fallback.review_id,
        match_id=record.match_id,
        season_index=record.season_index,
        author_id=author_id,
        target_id=target_id,
        target_role=target_role,
        text=text,
        rating=rating,
        created_at_match=record.season_index,
    )


class GossipStore:
    """Append-only store of published gossip with capped recent retrieval."""

    def __init__(self) -> None:
        self._records: list[GossipRecord] = []

    def add(self, record: GossipRecord) -> None:
        self._records.append(record)

    def recent_about(self, target_id: str, k: int) -> list[GossipRecord]:
        """Return up to ``k`` most recent reviews about ``target_id``."""
        if k <= 0:
            return []
        about = [r for r in self._records if r.target_id == target_id]
        return about[-k:]

    @property
    def records(self) -> list[GossipRecord]:
        return list(self._records)
