"""Diagnostic probe for the expected_value proposer strategy.

Runs a small number of Gemma rounds across three audit/penalty cells to
validate prompt calibration without executing the full 144-run sweep.

Requires Ollama running locally with a Gemma model pulled:

    ollama pull gemma3
    python scripts/probe_gemma3_expected_value.py --model gemma3

No API keys required.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from ultimatum_arena.llm.errors import (
    LLMError,
    LLMParseError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)
from ultimatum_arena.llm.ollama_client import OllamaLLMClient
from ultimatum_arena.runners.llm_sweep import _save_combined_csv, run_llm_strategy_sweep

OUTPUT_ROOT = _repo_root / "outputs" / "gemma3_expected_value_probe"

# ---------------------------------------------------------------------------
# Pure helpers (importable without side effects)
# ---------------------------------------------------------------------------

def _probe_cells() -> list[tuple[float, float]]:
    """Return the canonical (audit_prob, lie_penalty) cells for this probe."""
    return [
        (0.0,  0.0),   # zero audit risk -- underclaiming should dominate
        (0.25, 25.0),  # moderate risk
        (1.0,  50.0),  # maximum risk -- honest reporting should dominate
    ]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnostic probe: run expected_value strategy across three "
            "audit/penalty cells to validate prompt calibration."
        )
    )
    parser.add_argument(
        "--model",
        default="gemma3",
        help="Ollama model tag (default: gemma3)",
    )
    parser.add_argument(
        "--rounds",
        default=10,
        type=int,
        help="Rounds per cell (default: 10)",
    )
    parser.add_argument(
        "--seed",
        default=1,
        type=int,
        help="RNG seed (default: 1)",
    )
    parser.add_argument(
        "--temperature",
        default=0.2,
        type=float,
        help="Sampling temperature (default: 0.2)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_section(title: str) -> None:
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _print_table(rows: list[dict]) -> None:
    """Print a compact summary table for the probe results."""
    columns = [
        ("audit_prob",          "audit_prob",          8),
        ("lie_penalty",         "lie_penalty",          10),
        ("deception_rate",      "deception",            10),
        ("acceptance_rate",     "accept",               8),
        ("proposer_mean_payoff", "prop_payoff",         12),
        ("responder_mean_payoff", "resp_payoff",        12),
    ]
    header = "  " + "  ".join(f"{label:>{width}}" for _, label, width in columns)
    separator = "  " + "  ".join("-" * width for _, _, width in columns)
    print(header)
    print(separator)
    for row in rows:
        cells = []
        for key, _, width in columns:
            val = row.get(key, "")
            if isinstance(val, float):
                cells.append(f"{val:>{width}.4f}")
            else:
                cells.append(f"{str(val):>{width}}")
        print("  " + "  ".join(cells))


def _save_probe_manifest(
    output_dir: Path,
    *,
    cells: list[tuple[float, float]],
    args: argparse.Namespace,
) -> None:
    """Save metadata for the paired-cell probe run."""
    manifest = {
        "experiment_prefix": "gemma_ev_probe",
        "strategies": ["expected_value"],
        "cells": [
            {"audit_prob": audit_prob, "lie_penalty": lie_penalty}
            for audit_prob, lie_penalty in cells
        ],
        "seeds": [args.seed],
        "n_rounds": args.rounds,
        "n_cells": len(cells),
        "model": args.model,
        "temperature": args.temperature,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_ROOT / run_id

    cells = _probe_cells()

    _print_section("Expected-Value Strategy Probe (Gemma 3)")
    print(f"  Model       : {args.model}")
    print(f"  Rounds/cell : {args.rounds}")
    print(f"  Seed        : {args.seed}")
    print(f"  Temperature : {args.temperature}")
    print(f"  Cells       : {cells}")
    print(f"  Output dir  : {output_dir.resolve()}")

    def _client_factory() -> OllamaLLMClient:
        return OllamaLLMClient(model=args.model, temperature=args.temperature)

    try:
        all_rows: list[dict] = []
        for audit_prob, lie_penalty in cells:
            cell_rows = run_llm_strategy_sweep(
                proposer_client_factory=_client_factory,
                responder_client_factory=_client_factory,
                strategies=["expected_value"],
                audit_probabilities=[audit_prob],
                lie_penalties=[lie_penalty],
                seeds=[args.seed],
                n_rounds=args.rounds,
                output_dir=output_dir,
                experiment_prefix="gemma_ev_probe",
            )
            all_rows.extend(cell_rows)
        # Rewrite combined CSV with all paired-cell rows (not a Cartesian product).
        _save_combined_csv(all_rows, output_dir / "combined_summary.csv")
        _save_probe_manifest(output_dir, cells=cells, args=args)
        rows = all_rows
    except OllamaConnectionError as exc:
        print(f"\nERROR: Cannot connect to Ollama.\n  {exc}", file=sys.stderr)
        print("  -> Confirm Ollama is running:  ollama serve", file=sys.stderr)
        print(f"  -> Pull the model if needed:   ollama pull {args.model}", file=sys.stderr)
        sys.exit(1)
    except OllamaModelNotFoundError as exc:
        print(f"\nERROR: Model not found in Ollama.\n  {exc}", file=sys.stderr)
        print(f"  -> Run: ollama pull {args.model}", file=sys.stderr)
        sys.exit(1)
    except LLMParseError as exc:
        print(f"\nERROR: Model returned unparsable output.\n  {exc}", file=sys.stderr)
        print("  -> Rerun -- the model may produce valid JSON on the next attempt.", file=sys.stderr)
        sys.exit(1)
    except LLMError as exc:
        print(f"\nERROR: LLM error during sweep.\n  {exc}", file=sys.stderr)
        sys.exit(1)

    _print_section("Results")
    _print_table(rows)

    print(f"\n  Output directory: {output_dir.resolve()}")
    _print_section("Done")
    print()


if __name__ == "__main__":
    main()
