"""Lightweight helpers for summarizing LLM strategy sweep results.

No pandas or heavy statistics dependencies; pure Python only.
"""

from __future__ import annotations

_SUMMARY_KEYS = (
    "deception_rate",
    "proposer_mean_payoff",
    "proposer_advantage",
    "lie_detection_rate_among_lies",
)


def summarize_strategy_by_audit_risk(
    rows: list[dict],
    strategy: str,
    *,
    lie_penalty: float | None = None,
) -> list[dict]:
    """Summarize deception and payoff trends for one strategy across audit risk.

    Parameters
    ----------
    rows:
        List of sweep result dicts, each containing at minimum ``strategy``,
        ``audit_prob``, and the metric keys used here.
    strategy:
        Strategy name to filter on (e.g. ``"risk_aware"``).
    lie_penalty:
        If provided, only rows with this exact lie penalty are included.
        If ``None``, all lie penalties are included and the averages are
        computed across both seeds and penalties.

    Returns
    -------
    list[dict]
        One row per unique ``audit_prob`` value, sorted numerically, each with:
        ``strategy``, ``audit_prob``, ``n_runs``,
        ``deception_rate``, ``proposer_mean_payoff``,
        ``proposer_advantage``, ``lie_detection_rate_among_lies``.

    Raises
    ------
    ValueError
        If no rows match the given strategy (and optional lie_penalty).
    """
    # Filter by strategy
    filtered = [r for r in rows if r.get("strategy") == strategy]

    # Optionally filter by lie_penalty (compare as float to handle CSV strings)
    if lie_penalty is not None:
        filtered = [
            r for r in filtered
            if r.get("lie_penalty") is not None
            and float(r["lie_penalty"]) == lie_penalty
        ]

    if not filtered:
        raise ValueError(
            f"No rows found for strategy={strategy!r}"
            + (f", lie_penalty={lie_penalty}" if lie_penalty is not None else "")
        )

    # Group by audit_prob, coercing to float so CSV strings sort and compare correctly
    groups: dict[float, list[dict]] = {}
    for row in filtered:
        ap = float(row["audit_prob"])
        groups.setdefault(ap, []).append(row)

    result = []
    for audit_prob in sorted(groups):
        group = groups[audit_prob]
        n_runs = len(group)
        summary: dict = {
            "strategy": strategy,
            "audit_prob": audit_prob,
            "n_runs": n_runs,
        }
        for key in _SUMMARY_KEYS:
            vals = [
                float(r[key])
                for r in group
                if key in r and r[key] is not None and r[key] != ""
            ]
            summary[key] = sum(vals) / len(vals) if vals else float("nan")
        result.append(summary)

    return result
