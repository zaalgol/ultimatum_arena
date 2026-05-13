"""Phase 1 demo: Hidden Pie Ultimatum Game with heuristic agents.

Run from the repository root:

    python scripts/run_hidden_pie_demo.py

Each run writes to a new timestamped folder under outputs/hidden_pie_demo/.
No API keys or external services required.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Allow running from any working directory as long as the repo root is a parent.
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from ultimatum_arena.agents.proposers import LyingGreedyProposer
from ultimatum_arena.agents.responders import ThresholdResponder
from ultimatum_arena.analysis.plots import plot_metric_by_audit_prob
from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
from ultimatum_arena.runners.basic import run_experiment
from ultimatum_arena.runners.sweep import run_audit_penalty_sweep

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_ROOT = _repo_root / "outputs" / "hidden_pie_demo"

SINGLE_RUN_SEED = 42
N_ROUNDS = 200

AUDIT_PROBABILITIES = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
LIE_PENALTIES = [0.0, 10.0, 25.0, 50.0]
SEEDS = [1, 2, 3]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_section(title: str) -> None:
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _print_metrics(metrics: dict, label: str = "") -> None:
    prefix = f"[{label}] " if label else ""
    interesting = [
        ("acceptance_rate",           "Acceptance rate"),
        ("deception_rate",            "Deception rate"),
        ("detected_lie_rate",         "Detected lie rate"),
        ("lie_detection_rate_among_lies", "Detection rate among lies"),
        ("proposer_mean_payoff",      "Proposer mean payoff"),
        ("responder_mean_payoff",     "Responder mean payoff"),
        ("proposer_advantage",        "Proposer advantage"),
        ("mean_lie_size",             "Mean lie size"),
        ("mean_relative_lie_size",    "Mean relative lie size"),
    ]
    for key, label_str in interesting:
        if key in metrics:
            val = metrics[key]
            print(f"  {prefix}{label_str:<40} {val:.4f}")


# ---------------------------------------------------------------------------
# 1. Single experiment
# ---------------------------------------------------------------------------

def run_single(output_dir: Path) -> dict:
    _print_section("Single Experiment")
    print(f"  Proposer : LyingGreedyProposer(claimed_fraction=0.6, offer_fraction=0.4)")
    print(f"  Responder: ThresholdResponder(min_fraction=0.3)")
    print(f"  Rounds   : {N_ROUNDS}   Seed: {SINGLE_RUN_SEED}")

    proposer = LyingGreedyProposer(claimed_fraction=0.6, offer_fraction=0.4)
    responder = ThresholdResponder(min_fraction=0.3)
    env = HiddenPieAuditEnv(
        pie_range=(50.0, 150.0),
        audit_prob=0.25,
        lie_penalty=10.0,
        rng_seed=SINGLE_RUN_SEED,
    )

    _, metrics = run_experiment(
        proposer, responder, env, N_ROUNDS,
        output_dir=output_dir,
        experiment_name="single_run",
    )

    print()
    _print_metrics(metrics)
    print(f"\n  JSONL    : {output_dir / 'single_run.jsonl'}")
    print(f"  Summary  : {output_dir / 'single_run_summary.json'}")
    return metrics


# ---------------------------------------------------------------------------
# 2. Sweep
# ---------------------------------------------------------------------------

def run_sweep(output_dir: Path) -> list[dict]:
    _print_section("Audit-Penalty Sweep")
    print(f"  audit_probabilities : {AUDIT_PROBABILITIES}")
    print(f"  lie_penalties       : {LIE_PENALTIES}")
    print(f"  seeds               : {SEEDS}")
    print(f"  Rounds per cell     : {N_ROUNDS}")
    total_runs = len(AUDIT_PROBABILITIES) * len(LIE_PENALTIES) * len(SEEDS)
    print(f"  Total runs          : {total_runs}")

    rows = run_audit_penalty_sweep(
        audit_probabilities=AUDIT_PROBABILITIES,
        lie_penalties=LIE_PENALTIES,
        proposer_factory=lambda: LyingGreedyProposer(
            claimed_fraction=0.6, offer_fraction=0.4
        ),
        responder_factory=lambda: ThresholdResponder(min_fraction=0.3),
        n_rounds=N_ROUNDS,
        seeds=SEEDS,
        output_dir=output_dir,
        experiment_prefix="sweep",
    )

    csv_path = output_dir / "sweep_summary.csv"
    print(f"\n  Rows written : {len(rows)}")
    print(f"  CSV          : {csv_path}")
    return rows


# ---------------------------------------------------------------------------
# 3. Plots
# ---------------------------------------------------------------------------

def make_plots(rows: list[dict], plots_dir: Path) -> None:
    _print_section("Generating Plots")
    plots_dir.mkdir(parents=True, exist_ok=True)

    specs = [
        ("deception_rate",        "deception_rate_vs_audit_prob.png"),
        ("proposer_mean_payoff",   "proposer_mean_payoff_vs_audit_prob.png"),
        ("acceptance_rate",        "acceptance_rate_vs_audit_prob.png"),
    ]

    for metric, filename in specs:
        out = plots_dir / filename
        plot_metric_by_audit_prob(rows, metric, out, group_by="lie_penalty")
        print(f"  {filename}")


# ---------------------------------------------------------------------------
# 4. Aggregate sweep summary
# ---------------------------------------------------------------------------

def print_sweep_highlights(rows: list[dict]) -> None:
    _print_section("Sweep Highlights (averaged across seeds)")

    # Group by (audit_prob, lie_penalty) and average
    from collections import defaultdict
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[(row["audit_prob"], row["lie_penalty"])].append(row)

    metrics_to_show = ["acceptance_rate", "deception_rate", "proposer_mean_payoff"]
    header_parts = ["audit_prob", "lie_penalty"] + metrics_to_show
    col_w = 20
    header = "".join(f"{h:<{col_w}}" for h in header_parts)
    print(f"\n  {header}")
    print(f"  {'-' * (col_w * len(header_parts))}")

    for (ap, lp), group_rows in sorted(buckets.items()):
        avg = {}
        for m in metrics_to_show:
            vals = [r[m] for r in group_rows if m in r]
            avg[m] = sum(vals) / len(vals) if vals else float("nan")
        row_parts = [f"{ap:<{col_w}}", f"{lp:<{col_w}}"]
        row_parts += [f"{avg[m]:<{col_w}.4f}" for m in metrics_to_show]
        print(f"  {''.join(row_parts)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_ROOT / run_id
    single_run_dir = output_dir / "single_run"
    sweep_dir = output_dir / "sweep"
    plots_dir = output_dir / "plots"

    print(f"\nPhase 1 Demo — Hidden Pie Ultimatum Game")
    print(f"Run ID          : {run_id}")
    print(f"Output directory: {output_dir.resolve()}")

    single_run_dir.mkdir(parents=True, exist_ok=True)
    sweep_dir.mkdir(parents=True, exist_ok=True)

    run_single(single_run_dir)
    rows = run_sweep(sweep_dir)
    make_plots(rows, plots_dir)
    print_sweep_highlights(rows)

    _print_section("Done")
    print(f"  All outputs under: {output_dir.resolve()}")
    print()


if __name__ == "__main__":
    main()
