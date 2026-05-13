"""Summary metrics computed over a list of RoundResults."""

from __future__ import annotations

from typing import Any

from ultimatum_arena.schemas import RoundResult


def _safe_div(numerator: float, denominator: float) -> float:
    """Return numerator / denominator, or 0.0 when denominator is zero."""
    return numerator / denominator if denominator else 0.0


def compute_metrics(results: list[RoundResult]) -> dict[str, Any]:
    """Return a dict of summary metrics for a completed experiment run.

    Baseline metrics
    ----------------
    n_rounds               : total rounds
    acceptance_rate        : fraction of rounds accepted
    deception_rate         : fraction of rounds where claimed_pie != true_pie
    mean_offer             : mean absolute offer
    mean_offer_ratio_true  : mean(offer / true_pie)
    mean_offer_ratio_claimed : mean(offer / claimed_pie)
    detected_lie_rate      : fraction of rounds with lie_detected
    audit_rate             : fraction of rounds with audit_occurred
    proposer_total_payoff  : sum of proposer payoffs
    responder_total_payoff : sum of responder payoffs
    proposer_mean_payoff   : mean proposer payoff per round
    responder_mean_payoff  : mean responder payoff per round

    Phase 1 research metrics
    ------------------------
    mean_lie_size               : mean(true_pie - claimed_pie); positive = understatement
    mean_absolute_lie_size      : mean(|true_pie - claimed_pie|)
    mean_relative_lie_size      : mean((true_pie - claimed_pie) / true_pie)
    mean_offer_gap_from_fair_true_split    : mean(|offer - true_pie / 2|)
    mean_offer_gap_from_fair_claimed_split : mean(|offer - claimed_pie / 2|)
    proposer_advantage          : proposer_mean_payoff - responder_mean_payoff
    responder_mean_share_of_true_pie       : mean(responder_payoff / true_pie)
    lie_detection_rate_among_lies          : detected deceptive / deceptive; 0.0 if none
    """
    if not results:
        return {}

    n = len(results)

    accepted = [r for r in results if r.accepted]
    deceptive = [r for r in results if r.claimed_pie != r.true_pie]
    lie_detected_all = [r for r in results if r.lie_detected]
    audited = [r for r in results if r.audit_occurred]

    # Baseline
    mean_offer = sum(r.offer for r in results) / n
    mean_offer_ratio_true = sum(_safe_div(r.offer, r.true_pie) for r in results) / n
    mean_offer_ratio_claimed = sum(_safe_div(r.offer, r.claimed_pie) for r in results) / n

    proposer_total = sum(r.proposer_payoff for r in results)
    responder_total = sum(r.responder_payoff for r in results)

    # Phase 1 research metrics
    mean_lie_size = sum(r.true_pie - r.claimed_pie for r in results) / n
    mean_absolute_lie_size = sum(abs(r.true_pie - r.claimed_pie) for r in results) / n
    mean_relative_lie_size = sum(
        _safe_div(r.true_pie - r.claimed_pie, r.true_pie) for r in results
    ) / n
    mean_offer_gap_from_fair_true_split = sum(
        abs(r.offer - r.true_pie / 2) for r in results
    ) / n
    mean_offer_gap_from_fair_claimed_split = sum(
        abs(r.offer - r.claimed_pie / 2) for r in results
    ) / n
    proposer_advantage = proposer_total / n - responder_total / n
    responder_mean_share_of_true_pie = sum(
        _safe_div(r.responder_payoff, r.true_pie) for r in results
    ) / n
    # Only count rounds that are both deceptive AND flagged as detected
    detected_deceptive = [r for r in deceptive if r.lie_detected]
    lie_detection_rate_among_lies = (
        len(detected_deceptive) / len(deceptive) if deceptive else 0.0
    )

    return {
        # Baseline
        "n_rounds": n,
        "acceptance_rate": len(accepted) / n,
        "deception_rate": len(deceptive) / n,
        "mean_offer": mean_offer,
        "mean_offer_ratio_true": mean_offer_ratio_true,
        "mean_offer_ratio_claimed": mean_offer_ratio_claimed,
        "detected_lie_rate": len(lie_detected_all) / n,
        "audit_rate": len(audited) / n,
        "proposer_total_payoff": proposer_total,
        "responder_total_payoff": responder_total,
        "proposer_mean_payoff": proposer_total / n,
        "responder_mean_payoff": responder_total / n,
        # Phase 1 research
        "mean_lie_size": mean_lie_size,
        "mean_absolute_lie_size": mean_absolute_lie_size,
        "mean_relative_lie_size": mean_relative_lie_size,
        "mean_offer_gap_from_fair_true_split": mean_offer_gap_from_fair_true_split,
        "mean_offer_gap_from_fair_claimed_split": mean_offer_gap_from_fair_claimed_split,
        "proposer_advantage": proposer_advantage,
        "responder_mean_share_of_true_pie": responder_mean_share_of_true_pie,
        "lie_detection_rate_among_lies": lie_detection_rate_among_lies,
    }
