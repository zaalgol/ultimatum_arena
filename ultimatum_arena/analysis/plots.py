"""Plotting utilities for sweep results.

Uses the Agg (non-interactive) matplotlib backend so plots can be generated
in headless / test environments without a display.
"""

from __future__ import annotations

import collections
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # must be set before importing pyplot
import matplotlib.pyplot as plt


# Metrics written by save_aggregate_csv (in column order after config fields).
_AGGREGATE_METRICS = [
    "acceptance_rate",
    "deception_rate",
    "detected_lie_rate",
    "lie_detection_rate_among_lies",
    "proposer_mean_payoff",
    "responder_mean_payoff",
    "proposer_advantage",
]


def plot_metric_by_audit_prob(
    rows: list[dict],
    metric: str,
    output_path: str | Path,
    *,
    group_by: str | None = "lie_penalty",
) -> None:
    """Plot *metric* vs ``audit_prob``, optionally grouped by a second field.

    Parameters
    ----------
    rows:
        List of sweep result dicts as returned by
        :func:`~ultimatum_arena.runners.sweep.run_audit_penalty_sweep`.
        Each dict must contain ``audit_prob`` and *metric*.  When *group_by*
        is set the field must also be present in every row.
    metric:
        Key of the metric to plot on the y-axis.
    output_path:
        Destination path for the saved PNG image.  Parent directories are
        created if they do not exist.
    group_by:
        Row field used to colour/separate series.  Defaults to
        ``"lie_penalty"``.  Pass ``None`` to plot a single series.

    Raises
    ------
    ValueError
        If *rows* is empty, any row is missing ``audit_prob`` or *metric*, any
        row is missing the *group_by* field, or any metric value cannot be
        converted to ``float``.
    """
    if not rows:
        raise ValueError("rows is empty; nothing to plot.")

    # Aggregate: average duplicate (audit_prob, group) pairs.
    # Validate every row inline so errors include the row index.
    accumulator: dict[tuple, list[float]] = collections.defaultdict(list)

    for i, row in enumerate(rows):
        if "audit_prob" not in row:
            raise ValueError(
                f"Row {i} is missing required field 'audit_prob'."
            )
        if metric not in row:
            raise ValueError(
                f"Row {i} is missing metric '{metric}'. "
                f"Available keys: {sorted(row.keys())}"
            )
        if group_by is not None and group_by not in row:
            raise ValueError(
                f"Row {i} is missing group_by field '{group_by}'. "
                f"Available keys: {sorted(row.keys())}"
            )
        try:
            value = float(row[metric])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Metric '{metric}' in row {i} cannot be converted to float: "
                f"{row[metric]!r}"
            ) from exc

        key = (
            row.get(group_by) if group_by is not None else None,
            row["audit_prob"],
        )
        accumulator[key].append(value)

    averaged: dict[tuple, float] = {
        k: sum(v) / len(v) for k, v in accumulator.items()
    }

    # Organise into series keyed by group label
    series: dict[object, dict[float, float]] = collections.defaultdict(dict)
    for (group_label, audit_prob), value in averaged.items():
        series[group_label][audit_prob] = value

    fig, ax = plt.subplots()

    for group_label, xy in sorted(series.items(), key=lambda item: str(item[0])):
        x_vals = sorted(xy.keys())
        y_vals = [xy[x] for x in x_vals]
        label = f"{group_by}={group_label}" if group_by is not None else metric
        ax.plot(x_vals, y_vals, marker="o", label=label)

    ax.set_xlabel("audit_prob")
    ax.set_ylabel(metric)
    ax.set_title(f"{metric} vs audit_prob")
    if group_by is not None:
        ax.legend(title=group_by)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, format="png")
    plt.close(fig)


def plot_metric_by_audit_prob_for_strategies(
    rows: list[dict],
    metric: str,
    output_path: str | Path,
    *,
    lie_penalty: float | None = None,
) -> None:
    """Plot *metric* vs ``audit_prob`` with one line per proposer strategy.

    This is a convenience wrapper around :func:`plot_metric_by_audit_prob` that
    groups by the ``"strategy"`` field.  When *lie_penalty* is provided only
    rows matching that penalty are included; otherwise all rows are used and
    values are averaged across lie penalties for each
    ``(strategy, audit_prob)`` pair.

    Parameters
    ----------
    rows:
        Sweep result dicts containing at least ``audit_prob``, ``strategy``,
        and *metric*.
    metric:
        Key of the metric to plot on the y-axis.
    output_path:
        Destination path for the saved PNG image.
    lie_penalty:
        If provided, filter rows to this ``lie_penalty`` value before plotting.

    Raises
    ------
    ValueError
        Propagated from :func:`plot_metric_by_audit_prob` when *rows* is empty
        or required fields are missing.
    """
    if lie_penalty is not None:
        rows = [r for r in rows if r.get("lie_penalty") == lie_penalty]
    plot_metric_by_audit_prob(rows, metric, output_path, group_by="strategy")


def save_aggregate_csv(rows: list[dict], output_path: str | Path) -> None:
    """Write an aggregate CSV grouped by ``(strategy, audit_prob, lie_penalty)``.

    Each output row represents one cell and contains ``n_runs`` (the number of
    rows—typically seeds—aggregated into it) plus the mean of the key research
    metrics.  Rows are sorted by ``(strategy, audit_prob, lie_penalty)``.

    An empty *rows* list writes an empty file without raising.

    Parameters
    ----------
    rows:
        Sweep result dicts as returned by
        :func:`~ultimatum_arena.runners.llm_sweep.run_llm_strategy_sweep`.
    output_path:
        Destination path for the CSV file.  Parent directories are created
        if they do not exist.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        output_path.write_text("", encoding="utf-8")
        return

    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (
            row.get("strategy"),
            row.get("audit_prob"),
            row.get("lie_penalty"),
        )
        groups.setdefault(key, []).append(row)

    out_rows: list[dict] = []
    for (strategy, audit_prob, lie_penalty), group in sorted(
        groups.items(),
        key=lambda kv: (str(kv[0][0]), float(kv[0][1] or 0), float(kv[0][2] or 0)),
    ):
        agg: dict = {
            "strategy": strategy,
            "audit_prob": audit_prob,
            "lie_penalty": lie_penalty,
            "n_runs": len(group),
        }
        for m in _AGGREGATE_METRICS:
            vals = [r[m] for r in group if m in r]
            agg[m] = sum(vals) / len(vals) if vals else None
        out_rows.append(agg)

    fieldnames = ["strategy", "audit_prob", "lie_penalty", "n_runs"] + _AGGREGATE_METRICS

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows)
