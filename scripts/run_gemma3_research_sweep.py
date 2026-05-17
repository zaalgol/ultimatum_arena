"""Gemma 3 research sweep: Hidden Pie Ultimatum across strategies, audit probs, and penalties.

Runs a full LLM strategy sweep via local Ollama/Gemma 3.  No API keys required.

Usage
-----
    # Quick smoke test (6 cells × 1 seed = 6 runs, 10 rounds each)
    python scripts/run_gemma3_research_sweep.py --preset smoke

    # Full research sweep (3 strategies × 6 audit probs × 4 penalties × 3 seeds = 216 runs)
    python scripts/run_gemma3_research_sweep.py --preset research

    # Risk-aware comparison (honest_fair vs deceptive vs risk_aware, 108 runs)
    python scripts/run_gemma3_research_sweep.py --preset risk --model gemma3

    # Custom override example
    python scripts/run_gemma3_research_sweep.py --preset smoke --rounds 20 --seeds 1 2

Requires Ollama running locally:
    ollama serve        (or it may already be running)
    ollama pull gemma3
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from ultimatum_arena.analysis.plots import (
    plot_metric_by_audit_prob_for_strategies,
    save_aggregate_csv,
)
from ultimatum_arena.analysis.sweep_summary import summarize_strategy_by_audit_risk
from ultimatum_arena.llm.errors import (
    LLMError,
    LLMParseError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)
from ultimatum_arena.llm.ollama_client import OllamaLLMClient
from ultimatum_arena.runners.llm_sweep import run_llm_strategy_sweep

OUTPUT_ROOT_DEFAULT = _repo_root / "outputs" / "gemma3_research"

# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

_PRESETS: dict[str, dict] = {
    "smoke": {
        "strategies": ["honest_fair", "deceptive"],
        "audit_probabilities": [0.0, 0.25, 1.0],
        "lie_penalties": [0.0, 25.0],
        "seeds": [1],
        "n_rounds": 10,
    },
    "research": {
        "strategies": ["honest_fair", "self_interested", "deceptive"],
        "audit_probabilities": [0.0, 0.1, 0.25, 0.5, 0.75, 1.0],
        "lie_penalties": [0.0, 10.0, 25.0, 50.0],
        "seeds": [1, 2, 3],
        "n_rounds": 50,
    },
    "risk": {
        "strategies": ["honest_fair", "deceptive", "risk_aware"],
        "audit_probabilities": [0.0, 0.25, 0.5, 1.0],
        "lie_penalties": [0.0, 25.0, 50.0],
        "seeds": [1, 2, 3],
        "n_rounds": 50,
    },
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Gemma 3 Hidden Pie research sweep via Ollama.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--preset",
        choices=list(_PRESETS),
        default="smoke",
        help="Configuration preset (default: smoke)",
    )
    parser.add_argument(
        "--model",
        default="gemma3",
        help="Ollama model tag (default: gemma3)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature (default: 0.2)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Override rounds per run",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        metavar="STRATEGY",
        default=None,
        help="Override strategies (e.g. --strategies honest_fair deceptive)",
    )
    parser.add_argument(
        "--audit-probs",
        nargs="+",
        type=float,
        metavar="P",
        default=None,
        help="Override audit probabilities (e.g. --audit-probs 0.0 0.25 1.0)",
    )
    parser.add_argument(
        "--lie-penalties",
        nargs="+",
        type=float,
        metavar="V",
        default=None,
        help="Override lie penalties (e.g. --lie-penalties 0 25 50)",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        metavar="S",
        default=None,
        help="Override RNG seeds (e.g. --seeds 1 2 3)",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=OUTPUT_ROOT_DEFAULT,
        help=f"Root directory for outputs (default: {OUTPUT_ROOT_DEFAULT})",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_SEP = "=" * 64


def _section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def _print_dimensions(cfg: dict) -> None:
    strategies = cfg["strategies"]
    audit_probs = cfg["audit_probabilities"]
    lie_penalties = cfg["lie_penalties"]
    seeds = cfg["seeds"]
    n_rounds = cfg["n_rounds"]
    n_cells = len(strategies) * len(audit_probs) * len(lie_penalties) * len(seeds)

    print(f"  Strategies        : {', '.join(strategies)}")
    print(f"  Audit probs       : {audit_probs}")
    print(f"  Lie penalties     : {lie_penalties}")
    print(f"  Seeds             : {seeds}")
    print(f"  Rounds per run    : {n_rounds}")
    print(f"  Total runs        : {n_cells}")


def _print_summary_table(rows: list[dict]) -> None:
    """Print a summary grouped by strategy, averaged over other dimensions."""
    if not rows:
        return

    # Group by strategy
    from collections import defaultdict
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["strategy"]].append(row)

    metrics = [
        ("acceptance_rate",    "Accept%"),
        ("deception_rate",     "Deception%"),
        ("detected_lie_rate",  "Detected%"),
        ("proposer_mean_payoff", "Prop.Payoff"),
        ("responder_mean_payoff", "Resp.Payoff"),
    ]

    # Header
    header = f"  {'Strategy':<18}" + "".join(f"  {label:>12}" for _, label in metrics)
    print(header)
    print("  " + "-" * (16 + 14 * len(metrics)))

    for strategy in ["honest_fair", "self_interested", "deceptive"]:
        group = groups.get(strategy, [])
        if not group:
            continue
        avgs = {}
        for key, _ in metrics:
            vals = [r[key] for r in group if key in r]
            avgs[key] = sum(vals) / len(vals) if vals else float("nan")
        row_str = f"  {strategy:<18}" + "".join(
            f"  {avgs[key]:>12.4f}" for key, _ in metrics
        )
        print(row_str)

    # Also print any strategies not in the canonical order
    canonical = {"honest_fair", "self_interested", "deceptive"}
    for strategy, group in sorted(groups.items()):
        if strategy in canonical:
            continue
        avgs = {}
        for key, _ in metrics:
            vals = [r[key] for r in group if key in r]
            avgs[key] = sum(vals) / len(vals) if vals else float("nan")
        row_str = f"  {strategy:<18}" + "".join(
            f"  {avgs[key]:>12.4f}" for key, _ in metrics
        )
        print(row_str)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # Build config from preset + overrides
    cfg = dict(_PRESETS[args.preset])
    if args.rounds is not None:
        cfg["n_rounds"] = args.rounds
    if args.strategies is not None:
        cfg["strategies"] = args.strategies
    if args.audit_probs is not None:
        cfg["audit_probabilities"] = args.audit_probs
    if args.lie_penalties is not None:
        cfg["lie_penalties"] = args.lie_penalties
    if args.seeds is not None:
        cfg["seeds"] = args.seeds

    now = datetime.now()
    run_id = now.strftime("%Y%m%d_%H%M%S")
    created_at = now.isoformat()
    output_dir = args.output_root / run_id

    _section("Gemma 3 Research Sweep")
    print(f"  Run ID            : {run_id}")
    print(f"  Output directory  : {output_dir.resolve()}")
    print(f"  Preset            : {args.preset}")
    print(f"  Model             : {args.model}")
    print(f"  Temperature       : {args.temperature}")
    _section("Sweep Dimensions")
    _print_dimensions(cfg)

    model = args.model
    temperature = args.temperature

    def proposer_client_factory() -> OllamaLLMClient:
        return OllamaLLMClient(model=model, temperature=temperature)

    def responder_client_factory() -> OllamaLLMClient:
        return OllamaLLMClient(model=model, temperature=temperature)

    _section("Running")
    print()

    try:
        rows = run_llm_strategy_sweep(
            proposer_client_factory=proposer_client_factory,
            responder_client_factory=responder_client_factory,
            strategies=cfg["strategies"],
            audit_probabilities=cfg["audit_probabilities"],
            lie_penalties=cfg["lie_penalties"],
            seeds=cfg["seeds"],
            n_rounds=cfg["n_rounds"],
            output_dir=output_dir,
            experiment_prefix="gemma_research",
            manifest_extra={
                "model": args.model,
                "temperature": args.temperature,
                "preset": args.preset,
                "run_id": run_id,
                "created_at": created_at,
                "script": "scripts/run_gemma3_research_sweep.py",
                "output_dir": str(output_dir.resolve()),
            },
        )
    except OllamaConnectionError as exc:
        print(f"\nERROR: Cannot connect to Ollama.\n  {exc}", file=sys.stderr)
        print("  → Confirm Ollama is running:  ollama serve", file=sys.stderr)
        print(f"  → Pull the model if needed:   ollama pull {args.model}", file=sys.stderr)
        print("  → Check available models:     ollama list", file=sys.stderr)
        sys.exit(1)
    except OllamaModelNotFoundError as exc:
        print(f"\nERROR: Model not found in Ollama.\n  {exc}", file=sys.stderr)
        print(f"  → Run: ollama pull {args.model}", file=sys.stderr)
        print("  → Check available models: ollama list", file=sys.stderr)
        sys.exit(1)
    except LLMParseError as exc:
        print(f"\nERROR: Model returned output that could not be parsed.\n  {exc}", file=sys.stderr)
        print("  → Rerun — the model may produce valid JSON on the next attempt.", file=sys.stderr)
        print("  → Consider improving prompts in ultimatum_arena/llm/prompts.py.", file=sys.stderr)
        sys.exit(1)
    except LLMError as exc:
        print(f"\nERROR: LLM error during sweep.\n  {exc}", file=sys.stderr)
        sys.exit(1)

    csv_path = output_dir / "combined_summary.csv"
    manifest_path = output_dir / "manifest.json"
    aggregate_path = output_dir / "aggregate_by_strategy_audit_penalty.csv"
    plots_dir = output_dir / "plots"

    # Aggregate CSV
    save_aggregate_csv(rows, aggregate_path)

    # Plots: one PNG per (metric, lie_penalty) to preserve the penalty dimension
    _plot_metrics = [
        "deception_rate",
        "proposer_mean_payoff",
        "acceptance_rate",
        "lie_detection_rate_among_lies",
    ]
    unique_penalties = sorted({r["lie_penalty"] for r in rows})
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_warnings: list[str] = []
    for lp in unique_penalties:
        lp_str = f"{lp:g}"  # "0", "10", "25", "50"
        for metric in _plot_metrics:
            out_path = plots_dir / f"{metric}_by_audit_prob_penalty_{lp_str}.png"
            try:
                plot_metric_by_audit_prob_for_strategies(
                    rows,
                    metric,
                    out_path,
                    lie_penalty=lp,
                )
            except (ValueError, KeyError) as exc:
                plot_warnings.append(f"  penalty={lp_str}, {metric}: {exc}")

    if plot_warnings:
        print("  WARNING: some plots could not be generated:")
        for w in plot_warnings:
            print(w)

    _section("Results by Strategy (averaged across other dimensions)")
    _print_summary_table(rows)

    # Optional risk-aware deception table
    if "risk_aware" in cfg["strategies"]:
        try:
            risk_rows = summarize_strategy_by_audit_risk(rows, "risk_aware")
            _section("Risk-aware deception by audit probability")
            header = (
                f"  {'audit_prob':>10}  {'deception_rate':>14}  "
                f"{'proposer_mean_payoff':>20}  {'proposer_advantage':>18}"
            )
            print(header)
            print("  " + "-" * 68)
            for r in risk_rows:
                print(
                    f"  {r['audit_prob']:>10.2f}  {r['deception_rate']:>14.4f}  "
                    f"  {r['proposer_mean_payoff']:>18.4f}  {r['proposer_advantage']:>18.4f}"
                )
        except ValueError:
            pass

    _section("Output")
    print(f"  Runs              : {output_dir / 'runs'}")
    print(f"  Combined CSV      : {csv_path}")
    print(f"  Aggregate CSV     : {aggregate_path}")
    print(f"  Plots             : {plots_dir}")
    print(f"  Manifest          : {manifest_path}")
    print(f"  Total rows        : {len(rows)}")

    _section("Done")
    print()


if __name__ == "__main__":
    main()
