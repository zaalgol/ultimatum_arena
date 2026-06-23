"""Comparison probe using OpenAI Responses API models.

Runs the same diagnostic as ``probe_expected_value_comparison.py`` but uses an
OpenAI-hosted model for the LLM strategies.  Requires ``OPENAI_API_KEY`` in the
environment.

Example:

    python scripts/probe_openai_expected_value_comparison.py
    python scripts/probe_openai_expected_value_comparison.py --model gpt-5.4-mini --rounds 3
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

from scripts.probe_expected_value_comparison import (  # noqa: E402
    DEFAULT_LLM_STRATEGIES,
    _probe_cells,
    _print_section,
    _print_table,
    _run_calculator_rows,
)
from ultimatum_arena.llm.errors import (  # noqa: E402
    LLMError,
    LLMParseError,
    OpenAIAPIKeyError,
    OpenAIConnectionError,
)
from ultimatum_arena.llm.openai_client import OpenAIResponsesClient  # noqa: E402
from ultimatum_arena.runners.llm_sweep import _save_combined_csv, run_llm_strategy_sweep  # noqa: E402


OUTPUT_ROOT = _repo_root / "outputs" / "openai_expected_value_comparison_probe"
DEFAULT_MODEL = "gpt-5.4-mini"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "OpenAI comparison probe: deterministic EV baseline vs OpenAI LLM "
            "strategies across three audit/penalty cells."
        )
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--rounds",
        default=10,
        type=int,
        help="Rounds per cell per strategy (default: 10)",
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
        help="Sampling temperature for OpenAI strategies (default: 0.2)",
    )
    parser.add_argument(
        "--max-output-tokens",
        default=512,
        type=int,
        help="Maximum output tokens per OpenAI response (default: 512)",
    )
    return parser.parse_args(argv)


def _save_openai_manifest(
    output_dir: Path,
    *,
    cells: list[tuple[float, float]],
    llm_strategies: list[str],
    args: argparse.Namespace,
) -> None:
    manifest = {
        "experiment_prefix": "openai_ev_comparison_probe",
        "provider": "openai",
        "calculator_strategy": "calculator_expected_value",
        "llm_strategies": llm_strategies,
        "all_strategies": ["calculator_expected_value"] + llm_strategies,
        "cells": [
            {"audit_prob": audit_prob, "lie_penalty": lie_penalty}
            for audit_prob, lie_penalty in cells
        ],
        "seeds": [args.seed],
        "n_rounds": args.rounds,
        "n_cells": len(cells),
        "model": args.model,
        "temperature": args.temperature,
        "max_output_tokens": args.max_output_tokens,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_ROOT / run_id
    cells = _probe_cells()
    llm_strategies = DEFAULT_LLM_STRATEGIES

    _print_section("OpenAI Expected-Value Comparison Probe")
    print(f"  Model          : {args.model}")
    print(f"  Rounds/cell    : {args.rounds}")
    print(f"  Seed           : {args.seed}")
    print(f"  Temperature    : {args.temperature}")
    print(f"  Max output tok : {args.max_output_tokens}")
    print(f"  Cells          : {cells}")
    print(f"  LLM strategies : {llm_strategies}")
    print(f"  Output dir     : {output_dir.resolve()}")

    def _client_factory() -> OpenAIResponsesClient:
        return OpenAIResponsesClient(
            model=args.model,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
            timeout=120.0,
        )

    try:
        calculator_rows = _run_calculator_rows(
            cells,
            n_rounds=args.rounds,
            seed=args.seed,
            output_dir=output_dir,
        )

        llm_rows: list[dict] = []
        for audit_prob, lie_penalty in cells:
            cell_rows = run_llm_strategy_sweep(
                proposer_client_factory=_client_factory,
                responder_client_factory=_client_factory,
                strategies=llm_strategies,
                audit_probabilities=[audit_prob],
                lie_penalties=[lie_penalty],
                seeds=[args.seed],
                n_rounds=args.rounds,
                output_dir=output_dir,
                experiment_prefix="openai_ev_comparison_probe",
            )
            llm_rows.extend(cell_rows)

    except OpenAIAPIKeyError as exc:
        print(f"\nERROR: OpenAI API key problem.\n  {exc}", file=sys.stderr)
        print('  -> Set it with: $env:OPENAI_API_KEY="..."', file=sys.stderr)
        print('  -> Or persist it with: setx OPENAI_API_KEY "..."', file=sys.stderr)
        sys.exit(1)
    except OpenAIConnectionError as exc:
        print(f"\nERROR: Cannot connect to OpenAI.\n  {exc}", file=sys.stderr)
        sys.exit(1)
    except LLMParseError as exc:
        print(f"\nERROR: Model returned unparsable output.\n  {exc}", file=sys.stderr)
        print("  -> Rerun or reduce temperature if this repeats.", file=sys.stderr)
        sys.exit(1)
    except LLMError as exc:
        print(f"\nERROR: LLM error during sweep.\n  {exc}", file=sys.stderr)
        sys.exit(1)

    all_rows = calculator_rows + llm_rows
    _save_combined_csv(all_rows, output_dir / "combined_summary.csv")
    _save_openai_manifest(output_dir, cells=cells, llm_strategies=llm_strategies, args=args)

    _print_section("Results")
    _print_table(all_rows)

    print(f"\n  Output directory: {output_dir.resolve()}")
    _print_section("Done")
    print()


if __name__ == "__main__":
    main()
