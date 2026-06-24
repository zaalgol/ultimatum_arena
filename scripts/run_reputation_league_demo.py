"""Reputation Network League demo.

Plays a season of one-shot Hidden Pie Audit matches across a population of
agents that accumulate payoff, public reputation, private memory, and optional
public gossip. Match-making is random or reputation-based.

The default is cheap and fully local: a deterministic **heuristic** roster with
no external services. Use ``--provider ollama`` for a local Gemma league,
``--provider claude`` for a tiny usage-window-aware Claude canary, or
``--provider openai`` only if explicitly requested (needs ``OPENAI_API_KEY``).

Examples (PowerShell)::

    # deterministic / heuristic smoke, no model calls
    python scripts/run_reputation_league_demo.py --provider heuristic --agents 8 --matches 40 --matching random

    # local Gemma smoke
    python scripts/run_reputation_league_demo.py --provider ollama --model gemma3 --agents 6 --matches 20 --matching random

    # local Gemma, reputation-based matching + deterministic gossip
    python scripts/run_reputation_league_demo.py --provider ollama --model gemma3 --agents 8 --matches 60 --matching reputation_based --gossip deterministic

    # tiny Claude CLI canary (expensive: each match is >=2 model calls)
    python scripts/run_reputation_league_demo.py --provider claude --model haiku --agents 4 --matches 8

Outputs are written under ``outputs/reputation_league/YYYYMMDD_HHMMSS/``.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from ultimatum_arena.agents import (
    ExpectedValueProposer,
    GreedyHonestProposer,
    HonestFairProposer,
    LyingGreedyProposer,
    SuspiciousResponder,
    ThresholdResponder,
)
from ultimatum_arena.league import (
    GossipConfig,
    HeuristicParticipant,
    LeagueAgentProfile,
    LeagueConfig,
    LLMParticipant,
    MemoryConfig,
    ReputationConfig,
    run_reputation_league,
    write_league_outputs,
)
from ultimatum_arena.llm.claude_cli_client import ClaudeCLIClient
from ultimatum_arena.llm.client import LLMClient
from ultimatum_arena.llm.errors import (
    ClaudeCLIError,
    LLMError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)
from ultimatum_arena.llm.ollama_client import OllamaLLMClient
from ultimatum_arena.llm.openai_client import OpenAIResponsesClient

OUTPUT_ROOT = _repo_root / "outputs" / "reputation_league"

# Heuristic archetypes cycled to fill the roster. Each is (label, proposer, responder).
_HEURISTIC_ARCHETYPES = [
    ("honest_fair", lambda: HonestFairProposer(), lambda: ThresholdResponder(min_fraction=0.3)),
    ("self_interested", lambda: GreedyHonestProposer(offer_fraction=0.2), lambda: ThresholdResponder(min_fraction=0.25)),
    ("deceptive", lambda: LyingGreedyProposer(claimed_fraction=0.6, offer_fraction=0.4), lambda: ThresholdResponder(min_fraction=0.25)),
    ("expected_value", lambda: ExpectedValueProposer(), lambda: ThresholdResponder(min_fraction=0.25)),
    ("suspicious", lambda: HonestFairProposer(), lambda: SuspiciousResponder(min_fraction=0.35)),
]

# LLM strategy / responder-mode rotation cycled to fill the roster.
_LLM_STRATEGIES = ["honest_fair", "self_interested", "deceptive", "risk_aware", "expected_value"]
_LLM_RESPONDER_MODES = ["standard", "robust"]

# Provider-specific default models, used when --model is not given. This keeps the
# client, participant profiles, printed output, and manifest all consistent with
# the model actually called (no gemma3 -> haiku silent mismatch in metadata).
PROVIDER_DEFAULT_MODELS = {"ollama": "gemma3", "claude": "haiku", "openai": "gpt-5.4-mini"}


def resolve_model(provider: str, model: str | None) -> str | None:
    """Resolve the effective model: explicit --model wins, else provider default."""
    if provider == "heuristic":
        return None
    return model or PROVIDER_DEFAULT_MODELS[provider]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reputation Network League demo.")
    parser.add_argument(
        "--provider",
        default="heuristic",
        choices=["heuristic", "ollama", "claude", "openai"],
        help="Agent backend (default: heuristic / no external services).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model tag for LLM providers. Default depends on provider: ollama=gemma3, claude=haiku, openai=gpt-5.4-mini.",
    )
    parser.add_argument("--agents", default=8, type=int, help="Number of agents (default: 8).")
    parser.add_argument("--matches", default=40, type=int, help="Number of matches in the season (default: 40).")
    parser.add_argument(
        "--matching",
        default="random",
        choices=["random", "reputation_based"],
        help="Match-making policy (default: random).",
    )
    parser.add_argument("--audit-prob", default=0.25, type=float, help="Audit probability (default: 0.25).")
    parser.add_argument("--lie-penalty", default=25.0, type=float, help="Lie penalty (default: 25.0).")
    parser.add_argument("--seed", default=1, type=int, help="RNG seed (default: 1).")
    parser.add_argument(
        "--gossip",
        default="off",
        choices=["off", "deterministic", "llm"],
        help="Gossip mode (default: off). 'llm' needs an LLM provider.",
    )
    parser.add_argument("--memory-limit", default=3, type=int, help="Private memory entries per opponent (default: 3).")
    parser.add_argument("--temperature", default=0.2, type=float, help="Sampling temperature (Ollama/OpenAI; default 0.2).")
    parser.add_argument("--output-root", default=None, help="Override output root directory.")
    return parser.parse_args(argv)


def _make_client(provider: str, model: str, temperature: float) -> LLMClient:
    if provider == "claude":
        return ClaudeCLIClient(model=model, timeout=180.0)
    if provider == "openai":
        return OpenAIResponsesClient(model=model, temperature=temperature)
    return OllamaLLMClient(model=model, temperature=temperature, timeout=120.0)


def build_participants(args: argparse.Namespace):
    """Build the roster for the chosen provider.

    Returns ``(participants, client, effective_model)`` so the caller can record
    the exact model used (resolved from provider defaults) in every artifact.
    """
    effective_model = resolve_model(args.provider, args.model)
    if args.provider == "heuristic":
        participants = []
        for i in range(args.agents):
            label, prop_factory, resp_factory = _HEURISTIC_ARCHETYPES[i % len(_HEURISTIC_ARCHETYPES)]
            profile = LeagueAgentProfile(
                agent_id=f"h{i:02d}",
                display_name=f"{label}-{i:02d}",
                kind="heuristic",
                proposer_strategy=label,
            )
            participants.append(HeuristicParticipant(profile, prop_factory(), resp_factory()))
        return participants, None, effective_model

    # LLM providers share a single client (one provider/model for the season).
    client = _make_client(args.provider, effective_model, args.temperature)
    participants = []
    for i in range(args.agents):
        strategy = _LLM_STRATEGIES[i % len(_LLM_STRATEGIES)]
        responder_mode = _LLM_RESPONDER_MODES[i % len(_LLM_RESPONDER_MODES)]
        profile = LeagueAgentProfile(
            agent_id=f"m{i:02d}",
            display_name=f"{strategy}-{i:02d}",
            kind="llm",
            proposer_strategy=strategy,
            responder_mode=responder_mode,
            model=effective_model,
            provider=args.provider,
        )
        participants.append(
            LLMParticipant(profile, client, strategy=strategy, responder_mode=responder_mode)
        )
    return participants, client, effective_model


def _print_section(title: str) -> None:
    width = 78
    print(f"\n{'=' * width}\n  {title}\n{'=' * width}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.gossip == "llm" and args.provider == "heuristic":
        print("ERROR: --gossip llm requires an LLM provider (ollama/claude/openai).", file=sys.stderr)
        sys.exit(2)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = Path(args.output_root) if args.output_root else OUTPUT_ROOT
    output_dir = output_root / run_id
    effective_model = resolve_model(args.provider, args.model)

    config = LeagueConfig(
        n_matches=args.matches,
        matching_policy=args.matching,
        audit_prob=args.audit_prob,
        lie_penalty=args.lie_penalty,
        rng_seed=args.seed,
        reputation=ReputationConfig(),
        memory=MemoryConfig(per_opponent_limit=args.memory_limit),
        gossip=GossipConfig(mode=args.gossip),
    )

    _print_section("Reputation Network League")
    print(f"  Provider   : {args.provider}")
    print(f"  Model      : {effective_model if effective_model else '(none)'}")
    print(f"  Agents     : {args.agents}")
    print(f"  Matches    : {args.matches}")
    print(f"  Matching   : {args.matching}")
    print(f"  Gossip     : {args.gossip}")
    print(f"  Audit/Pen  : {args.audit_prob} / {args.lie_penalty}")
    print(f"  Seed       : {args.seed}")
    print(f"  Output dir : {output_dir.resolve()}")

    # build_participants resolves the same effective_model internally; main already
    # computed it above for the header/manifest, so the third value is discarded.
    participants, gossip_client, _ = build_participants(args)

    try:
        result = run_reputation_league(participants, config, gossip_client=gossip_client)
    except OllamaConnectionError as exc:
        print(f"\nERROR: Cannot connect to Ollama.\n  {exc}\n  -> Start it: ollama serve", file=sys.stderr)
        sys.exit(1)
    except OllamaModelNotFoundError as exc:
        print(f"\nERROR: Model not found in Ollama.\n  {exc}\n  -> ollama pull {effective_model}", file=sys.stderr)
        sys.exit(1)
    except ClaudeCLIError as exc:
        print(f"\nERROR: Claude CLI call failed.\n  {exc}\n  -> Confirm Claude Code is installed and logged in.", file=sys.stderr)
        sys.exit(1)
    except LLMError as exc:
        print(f"\nERROR: LLM infrastructure error.\n  {exc}", file=sys.stderr)
        sys.exit(1)

    manifest = {
        "experiment": "reputation_league",
        "run_id": run_id,
        "provider": args.provider,
        "model": effective_model,
        "provider_label": (
            f"Claude Code CLI agents, model tier {effective_model}"
            if args.provider == "claude"
            else f"{args.provider} agents, model {effective_model}"
            if args.provider != "heuristic"
            else "heuristic agents (no model calls)"
        ),
        "n_agents": args.agents,
        "n_matches": args.matches,
        "matching_policy": args.matching,
        "gossip_mode": args.gossip,
        "audit_prob": args.audit_prob,
        "lie_penalty": args.lie_penalty,
        "seed": args.seed,
        "memory_limit": args.memory_limit,
        "temperature": args.temperature if args.provider in ("ollama", "openai") else None,
        "n_failures": len(result.failures),
        "config": config.model_dump(),
    }

    write_league_outputs(
        output_dir,
        manifest=manifest,
        records=result.records,
        failures=result.failures,
        final_states=result.final_states,
        gossip_records=result.gossip_records,
        reputation_history=result.reputation_history,
        summary=result.summary,
    )

    summary = result.summary
    _print_section("Leaderboard (top 5 by total payoff)")
    if summary.get("leaderboard"):
        print(f"  {'rank':<5}{'agent':<22}{'payoff':<12}{'reputation':<12}{'deception':<10}")
        for row in summary["leaderboard"][:5]:
            print(
                f"  {row['rank']:<5}{row['display_name']:<22}{row['total_payoff']:<12.1f}"
                f"{row['public_reputation']:<12.1f}{row['deception_count']:<10}"
            )

    _print_section("Season summary")
    print(f"  Matches played (ok)        : {len(result.records)}")
    print(f"  Refusals / parse failures  : {len(result.failures)}")
    if summary:
        print(f"  Total welfare              : {summary['total_welfare']:.1f}")
        print(f"  Payoff Gini (inequality)   : {summary['payoff_gini']:.3f}")
        print(f"  Deception rate             : {summary['deception_rate']:.3f}")
        print(f"  Detected-lie rate          : {summary['detected_lie_rate']:.3f}")
        print(f"  Acceptance rate            : {summary['acceptance_rate']:.3f}")
        print(f"  Mean offer ratio (true)    : {summary['mean_offer_ratio_true']:.3f}")
        corr = summary.get("reputation_payoff_correlation")
        print(f"  Reputation/payoff corr     : {corr:.3f}" if corr is not None else "  Reputation/payoff corr     : n/a")
        if args.gossip != "off":
            acc = summary.get("gossip_accuracy_vs_reputation")
            print(f"  Gossip reviews             : {summary.get('gossip_review_count')}")
            print(f"  Gossip accuracy vs rep     : {acc:.3f}" if acc is not None else "  Gossip accuracy vs rep     : n/a")

    _print_section("Done")
    print(f"  Output directory: {output_dir.resolve()}\n")


if __name__ == "__main__":
    main()
