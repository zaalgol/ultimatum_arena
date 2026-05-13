"""Sweep runner for audit_probability × lie_penalty × seed parameter grids."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Optional

from ultimatum_arena.agents.base import BaseProposer, BaseResponder
from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
from ultimatum_arena.runners.basic import run_experiment


# Config fields that always appear first in CSV output.
_CONFIG_FIELDS = [
    "audit_prob",
    "lie_penalty",
    "seed",
    "n_rounds",
    "proposer_class",
    "responder_class",
]


def save_sweep_csv(rows: list[dict], output_path: str | Path) -> None:
    """Write *rows* to a CSV file at *output_path*.

    Config fields appear first (audit_prob, lie_penalty, seed, n_rounds,
    proposer_class, responder_class), followed by all remaining metric fields.
    Fieldnames are collected from the union of all rows so that rows with
    differing keys are handled correctly.

    An empty *rows* list produces an empty file without raising.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        output_path.write_text("", encoding="utf-8")
        return

    # Collect all metric keys seen across every row, preserving insertion order.
    all_metric_keys: dict[str, None] = {}
    for row in rows:
        for k in row:
            if k not in _CONFIG_FIELDS:
                all_metric_keys[k] = None

    fieldnames = _CONFIG_FIELDS + list(all_metric_keys)

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_audit_penalty_sweep(
    audit_probabilities: list[float],
    lie_penalties: list[float],
    proposer_factory: Callable[[], BaseProposer],
    responder_factory: Callable[[], BaseResponder],
    pie_range: tuple[float, float] = (50.0, 150.0),
    n_rounds: int = 100,
    seeds: Optional[list[int]] = None,
    output_dir: Optional[Path | str] = None,
    experiment_prefix: str = "sweep",
) -> list[dict]:
    """Run a grid sweep over *audit_probabilities* × *lie_penalties* × *seeds*.

    For every (audit_prob, lie_penalty, seed) combination a fresh experiment
    is run.  Each returned row combines the configuration fields with the full
    metrics dict from :func:`~ultimatum_arena.analysis.metrics.compute_metrics`.

    Parameters
    ----------
    audit_probabilities:
        List of audit probability values to sweep over.
    lie_penalties:
        List of lie penalty values to sweep over.
    proposer_factory:
        Callable returning a fresh :class:`BaseProposer` for each cell.
    responder_factory:
        Callable returning a fresh :class:`BaseResponder` for each cell.
    pie_range:
        ``(min_pie, max_pie)`` passed to :class:`HiddenPieAuditEnv`.
    n_rounds:
        Rounds per cell.
    seeds:
        List of RNG seeds; one run is executed per seed.  Defaults to
        ``[42]`` when not provided.
    output_dir:
        If provided, per-cell JSONL + JSON files and a combined
        ``{experiment_prefix}_summary.csv`` are written here.
    experiment_prefix:
        Prefix for all output file names.

    Returns
    -------
    list[dict]
        One row per (audit_prob, lie_penalty, seed) cell, config fields first.
    """
    if seeds is None:
        seeds = [42]

    if output_dir is not None:
        output_dir = Path(output_dir)

    rows: list[dict] = []

    for audit_prob in audit_probabilities:
        for lie_penalty in lie_penalties:
            for seed in seeds:
                proposer = proposer_factory()
                responder = responder_factory()

                env = HiddenPieAuditEnv(
                    pie_range=pie_range,
                    audit_prob=audit_prob,
                    lie_penalty=lie_penalty,
                    rng_seed=seed,
                )

                # Sanitise floats/ints for use in filenames
                ap_tag = f"{audit_prob:.3f}".replace(".", "p")
                lp_tag = f"{lie_penalty:.3f}".replace(".", "p")
                exp_name = f"{experiment_prefix}_ap{ap_tag}_lp{lp_tag}_s{seed}"

                _, summary = run_experiment(
                    proposer,
                    responder,
                    env,
                    n_rounds,
                    output_dir=output_dir,
                    experiment_name=exp_name,
                )

                row: dict = {
                    "audit_prob": audit_prob,
                    "lie_penalty": lie_penalty,
                    "seed": seed,
                    "n_rounds": n_rounds,
                    "proposer_class": type(proposer).__name__,
                    "responder_class": type(responder).__name__,
                    **summary,
                }
                rows.append(row)

    if output_dir is not None:
        csv_path = output_dir / f"{experiment_prefix}_summary.csv"
        save_sweep_csv(rows, csv_path)

    return rows
