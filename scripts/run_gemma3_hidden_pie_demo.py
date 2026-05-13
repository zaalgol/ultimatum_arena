"""Gemma 3 demo: Hidden Pie Ultimatum Game with local LLM agents.

Requires Ollama running locally with the Gemma 3 model pulled:

    ollama pull gemma3
    python scripts/run_gemma3_hidden_pie_demo.py

Each run writes to a new timestamped folder under outputs/gemma3_demo/.
No API keys required.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Allow running from any working directory as long as the repo root is a parent.
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
from ultimatum_arena.llm.agents import LLMProposer, LLMResponder
from ultimatum_arena.llm.errors import (
    LLMError,
    LLMParseError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)
from ultimatum_arena.llm.ollama_client import OllamaLLMClient
from ultimatum_arena.runners.basic import run_experiment

OUTPUT_ROOT = _repo_root / "outputs" / "gemma3_demo"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Hidden Pie Ultimatum rounds with Gemma 3 via Ollama."
    )
    parser.add_argument("--model",        default="gemma3",  help="Ollama model tag (default: gemma3)")
    parser.add_argument("--rounds",       default=3,   type=int,   help="Number of rounds (default: 3)")
    parser.add_argument("--temperature",  default=0.2, type=float, help="Sampling temperature (default: 0.2)")
    parser.add_argument("--audit-prob",   default=0.25, type=float, help="Audit probability (default: 0.25)")
    parser.add_argument("--lie-penalty",  default=25.0, type=float, help="Lie penalty (default: 25.0)")
    parser.add_argument("--seed",         default=42,  type=int,   help="RNG seed (default: 42)")
    parser.add_argument(
        "--strategy",
        default="honest_fair",
        choices=["honest_fair", "self_interested", "deceptive"],
        help="Proposer strategy profile (default: honest_fair)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_section(title: str) -> None:
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _print_metrics(metrics: dict) -> None:
    keys = [
        ("acceptance_rate",   "Acceptance rate"),
        ("deception_rate",    "Deception rate"),
        ("detected_lie_rate", "Detected lie rate"),
        ("proposer_mean_payoff", "Proposer mean payoff"),
        ("responder_mean_payoff", "Responder mean payoff"),
    ]
    for key, label in keys:
        if key in metrics:
            print(f"  {label:<40} {metrics[key]:.4f}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_ROOT / run_id
    experiment_name = "gemma3_vs_gemma3"

    _print_section("Gemma 3 Hidden Pie Ultimatum Demo")
    print(f"  Run ID          : {run_id}")
    print(f"  Output directory: {output_dir.resolve()}")
    print(f"  Model           : {args.model}")
    print(f"  Rounds          : {args.rounds}")
    print(f"  Temperature     : {args.temperature}")
    print(f"  Audit prob      : {args.audit_prob}")
    print(f"  Lie penalty     : {args.lie_penalty}")
    print(f"  RNG seed        : {args.seed}")
    print(f"  Proposer strategy: {args.strategy}")

    proposer_client = OllamaLLMClient(model=args.model, temperature=args.temperature)
    responder_client = OllamaLLMClient(model=args.model, temperature=args.temperature)
    proposer = LLMProposer(proposer_client, strategy=args.strategy)
    responder = LLMResponder(responder_client)

    env = HiddenPieAuditEnv(
        pie_range=(50.0, 150.0),
        audit_prob=args.audit_prob,
        lie_penalty=args.lie_penalty,
        rng_seed=args.seed,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        _, metrics = run_experiment(
            proposer, responder, env, args.rounds,
            output_dir=output_dir,
            experiment_name=experiment_name,
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
        print(f"\nERROR: Gemma 3 returned output that could not be parsed.\n  {exc}", file=sys.stderr)
        print("  → Rerun — the model may produce valid JSON on the next attempt.", file=sys.stderr)
        print("  → Consider improving prompts in ultimatum_arena/llm/prompts.py.", file=sys.stderr)
        sys.exit(1)
    except LLMError as exc:
        print(f"\nERROR: LLM error during experiment.\n  {exc}", file=sys.stderr)
        sys.exit(1)

    _print_section("Results")
    _print_metrics(metrics)
    print(f"\n  JSONL  : {output_dir / (experiment_name + '.jsonl')}")
    print(f"  Summary: {output_dir / (experiment_name + '_summary.json')}")

    _print_section("Done")
    print()


if __name__ == "__main__":
    main()
