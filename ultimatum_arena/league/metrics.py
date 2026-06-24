"""Pure, deterministic league-level metrics.

``compute_league_metrics`` summarises a finished season from its match records,
final agent states, and (optionally) published gossip. Everything here is a pure
function of its inputs; it never calls a model. An empty record list returns
``{}`` (matching ``compute_metrics`` in the analysis package).
"""

from __future__ import annotations

from typing import Any, Sequence

from ultimatum_arena.league.schemas import (
    GossipRecord,
    LeagueAgentState,
    LeagueMatchRecord,
)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pearson correlation; ``None`` when undefined (too few points / no variance)."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mx, my = _mean(xs), _mean(ys)
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    if sx == 0 or sy == 0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / (sx * sy)


def _gini(values: Sequence[float]) -> float:
    """Gini coefficient of non-negative values; 0 when undefined.

    Payoffs can be negative (lie penalties); the values are shifted so the
    minimum is zero before computing, keeping the coefficient well defined.
    """
    if not values:
        return 0.0
    shift = min(values)
    adjusted = [v - shift for v in values]
    total = sum(adjusted)
    if total <= 0:
        return 0.0
    n = len(adjusted)
    ordered = sorted(adjusted)
    cumulative = sum((i + 1) * v for i, v in enumerate(ordered))
    return (2 * cumulative) / (n * total) - (n + 1) / n


def _segment_deception(records: Sequence[LeagueMatchRecord]) -> tuple[float, float]:
    """Deception rate in the first vs second half of the season (by order)."""
    if not records:
        return 0.0, 0.0
    half = len(records) // 2 or 1
    first = records[:half]
    second = records[half:] or first
    first_rate = _mean([1.0 if r.claimed_pie != r.true_pie else 0.0 for r in first])
    second_rate = _mean([1.0 if r.claimed_pie != r.true_pie else 0.0 for r in second])
    return first_rate, second_rate


def _leaderboard(final_states: Sequence[LeagueAgentState]) -> list[dict[str, Any]]:
    ordered = sorted(final_states, key=lambda s: s.total_payoff, reverse=True)
    return [
        {
            "rank": i + 1,
            "agent_id": s.profile.agent_id,
            "display_name": s.profile.display_name,
            "total_payoff": round(s.total_payoff, 3),
            "public_reputation": round(s.public_reputation, 3),
            "fairness_score": round(s.fairness_score, 4),
            "matches_played": s.matches_played,
            "deception_count": s.deception_count,
            "detected_lie_count": s.detected_lie_count,
        }
        for i, s in enumerate(ordered)
    ]


def _quartile_gap(final_states: Sequence[LeagueAgentState]) -> float:
    """Mean top-quartile payoff minus mean bottom-quartile payoff (exploitability)."""
    payoffs = sorted((s.total_payoff for s in final_states))
    n = len(payoffs)
    if n < 4:
        return 0.0
    q = n // 4
    bottom = payoffs[:q]
    top = payoffs[-q:]
    return _mean(top) - _mean(bottom)


def _gossip_metrics(
    gossip_records: Sequence[GossipRecord],
    final_states: Sequence[LeagueAgentState],
) -> dict[str, Any]:
    ratings = [g.rating for g in gossip_records if g.rating is not None]
    rep_by_id = {s.profile.agent_id: s.public_reputation for s in final_states}
    # Gossip accuracy: do reviews about a target track that target's final
    # reputation (a ground-truth-ish behaviour proxy)?
    paired_ratings: list[float] = []
    paired_reps: list[float] = []
    for g in gossip_records:
        if g.rating is not None and g.target_id in rep_by_id:
            paired_ratings.append(g.rating)
            paired_reps.append(rep_by_id[g.target_id])
    accuracy = _pearson(paired_ratings, paired_reps)
    return {
        "gossip_review_count": len(gossip_records),
        "gossip_mean_rating": _mean(ratings) if ratings else None,
        "gossip_accuracy_vs_reputation": accuracy,
    }


def compute_league_metrics(
    records: Sequence[LeagueMatchRecord],
    final_states: Sequence[LeagueAgentState],
    gossip_records: Sequence[GossipRecord] | None = None,
) -> dict[str, Any]:
    """Compute season-level metrics. Returns ``{}`` for no records."""
    if not records:
        return {}

    n = len(records)
    accepted = [r for r in records if r.accepted]
    deceptive = [r for r in records if r.claimed_pie != r.true_pie]
    detected = [r for r in records if r.lie_detected]

    offer_ratio_true = [r.offer / r.true_pie for r in records if r.true_pie > 0]
    offer_ratio_claimed = [r.offer / r.claimed_pie for r in records if r.claimed_pie > 0]

    payoffs = [s.total_payoff for s in final_states]
    reputations = [s.public_reputation for s in final_states]
    acceptance_rates = [
        (s.accepted_matches / s.matches_as_proposer) if s.matches_as_proposer else 0.0
        for s in final_states
    ]

    first_dec, second_dec = _segment_deception(records)

    metrics: dict[str, Any] = {
        "n_matches": n,
        "n_agents": len(final_states),
        "total_welfare": round(sum(payoffs), 3),
        "mean_agent_payoff": round(_mean(payoffs), 3),
        "payoff_std": round(_std(payoffs), 3),
        "payoff_gini": round(_gini(payoffs), 4),
        "exploitability_quartile_gap": round(_quartile_gap(final_states), 3),
        "acceptance_rate": len(accepted) / n,
        "deception_rate": len(deceptive) / n,
        "detected_lie_rate": len(detected) / n,
        "mean_offer": _mean([r.offer for r in records]),
        "mean_offer_ratio_true": _mean(offer_ratio_true),
        "mean_offer_ratio_claimed": _mean(offer_ratio_claimed),
        "fairness_gap_from_equal_true_split": abs(0.5 - _mean(offer_ratio_true)),
        "deception_rate_first_half": first_dec,
        "deception_rate_second_half": second_dec,
        "deception_rate_change": second_dec - first_dec,
        "reputation_payoff_correlation": _pearson(reputations, payoffs),
        "reputation_acceptance_correlation": _pearson(reputations, acceptance_rates),
        "opponent_reputation_acceptance_correlation": _pearson(
            [r.proposer_reputation_before for r in records],
            [1.0 if r.accepted else 0.0 for r in records],
        ),
        "leaderboard": _leaderboard(final_states),
    }

    if gossip_records:
        metrics.update(_gossip_metrics(gossip_records, final_states))

    return metrics
