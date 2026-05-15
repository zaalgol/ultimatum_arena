"""LLM strategy sweep runner for Hidden Pie + Audit experiments."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable, Optional

from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
from ultimatum_arena.llm.agents import LLMProposer, LLMResponder
from ultimatum_arena.llm.client import LLMClient
from ultimatum_arena.runners.basic import run_experiment

# Config fields that always appear first in CSV output.
_LLM_CONFIG_FIELDS = [
    "strategy",
    "audit_prob",
    "lie_penalty",
    "seed",
    "n_rounds",
    "model",
    "temperature",
    "proposer_class",
    "responder_class",
]


def _sanitize(value: float) -> str:
    """Convert a float to a filename-safe string (replaces '.' with 'p')."""
    return f"{value:.3f}".replace(".", "p")


def _save_combined_csv(rows: list[dict], output_path: Path) -> None:
    """Write *rows* to *output_path* with config fields first."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        output_path.write_text("", encoding="utf-8")
        return

    all_metric_keys: dict[str, None] = {}
    for row in rows:
        for k in row:
            if k not in _LLM_CONFIG_FIELDS:
                all_metric_keys[k] = None

    fieldnames = _LLM_CONFIG_FIELDS + list(all_metric_keys)

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_llm_strategy_sweep(
    *,
    proposer_client_factory: Callable[[], LLMClient],
    responder_client_factory: Callable[[], LLMClient],
    strategies: list[str],
    audit_probabilities: list[float],
    lie_penalties: list[float],
    seeds: list[int],
    n_rounds: int,
    pie_range: tuple[float, float] = (50.0, 150.0),
    output_dir: Optional[str | Path] = None,
    experiment_prefix: str = "gemma_strategy_sweep",
    manifest_extra: Optional[dict] = None,
) -> list[dict]:
    """Run a grid sweep over strategies × audit_probabilities × lie_penalties × seeds.

    For every combination a fresh ``HiddenPieAuditEnv``, ``LLMProposer``, and
    ``LLMResponder`` are created via the supplied factory callables.

    Parameters
    ----------
    proposer_client_factory:
        Called once per run; must return a fresh :class:`LLMClient`.
    responder_client_factory:
        Called once per run; must return a fresh :class:`LLMClient`.
    strategies:
        Proposer strategy profiles to sweep over.  Each value is passed to
        :class:`LLMProposer`; invalid values raise :class:`ValueError`.
    audit_probabilities:
        Audit probability values to sweep over.
    lie_penalties:
        Lie penalty values to sweep over.
    seeds:
        RNG seeds; one run is executed per seed.
    n_rounds:
        Rounds per run.
    pie_range:
        ``(min_pie, max_pie)`` passed to :class:`HiddenPieAuditEnv`.
    output_dir:
        If provided, per-run JSONL and summary JSON files are written under
        ``output_dir/runs/``.  ``combined_summary.csv`` and ``manifest.json``
        are written at the root of ``output_dir``.
    experiment_prefix:
        Prefix used in all run names and output file names.
    manifest_extra:
        Optional dict of additional fields to merge into ``manifest.json``
        (e.g. model, temperature, preset, run_id, created_at).  These fields
        are appended after the standard sweep-dimension fields.

    Returns
    -------
    list[dict]
        One row per ``(strategy, audit_prob, lie_penalty, seed)`` cell.
        Config fields appear first, followed by all metrics from
        :func:`~ultimatum_arena.analysis.metrics.compute_metrics`.
    """
    if output_dir is not None:
        output_dir = Path(output_dir)
        runs_dir = output_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
    else:
        runs_dir = None

    rows: list[dict] = []

    for strategy in strategies:
        for audit_prob in audit_probabilities:
            for lie_penalty in lie_penalties:
                for seed in seeds:
                    prop_client = proposer_client_factory()
                    resp_client = responder_client_factory()

                    proposer = LLMProposer(prop_client, strategy=strategy)
                    responder = LLMResponder(resp_client)

                    env = HiddenPieAuditEnv(
                        pie_range=pie_range,
                        audit_prob=audit_prob,
                        lie_penalty=lie_penalty,
                        rng_seed=seed,
                    )

                    strat_tag = strategy.replace("_", "-")
                    ap_tag = _sanitize(audit_prob)
                    lp_tag = _sanitize(lie_penalty)
                    run_name = (
                        f"{experiment_prefix}_strategy-{strat_tag}"
                        f"_audit-{ap_tag}_penalty-{lp_tag}_seed-{seed}"
                    )

                    _, summary = run_experiment(
                        proposer,
                        responder,
                        env,
                        n_rounds,
                        output_dir=runs_dir,
                        experiment_name=run_name,
                    )

                    model = getattr(prop_client, "model", None)
                    temperature = getattr(prop_client, "temperature", None)

                    row: dict = {
                        "strategy": strategy,
                        "audit_prob": audit_prob,
                        "lie_penalty": lie_penalty,
                        "seed": seed,
                        "n_rounds": n_rounds,
                        "model": model,
                        "temperature": temperature,
                        "proposer_class": type(proposer).__name__,
                        "responder_class": type(responder).__name__,
                        **summary,
                    }
                    rows.append(row)

    if output_dir is not None:
        _save_combined_csv(rows, output_dir / "combined_summary.csv")

        manifest: dict = {
            "experiment_prefix": experiment_prefix,
            "strategies": strategies,
            "audit_probabilities": audit_probabilities,
            "lie_penalties": lie_penalties,
            "seeds": seeds,
            "n_rounds": n_rounds,
            "pie_range": list(pie_range),
            "n_cells": len(rows),
        }
        if manifest_extra:
            manifest.update(manifest_extra)
        with (output_dir / "manifest.json").open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

    return rows
