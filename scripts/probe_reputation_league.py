"""Controlled reputation/gossip probe (responder-side).

Isolates whether an LLM **responder** changes its accept/reject decision based on
an opponent's social standing while the economic terms are held identical. For
each offer level we present the SAME fixed observation under two contexts:

* ``good``  — high public reputation, positive private memory, positive gossip.
* ``bad``   — low public reputation, negative private memory, negative gossip.

Each repeat is **paired** (the same observation is shown under both contexts), so
the probe reports two complementary signals: ``reputation_effect`` — the
acceptance *delta* (good_accept_rate - bad_accept_rate) — and the true per-repeat
**decision flip** counts ``good_only_accepts`` (accepted under good reputation but
rejected under bad on the same repeat), ``bad_only_accepts``, and
``same_decision``. Heuristic agents are reputation-blind (a deterministic
control); LLMs may not be.

This probe makes two model calls per (offer, repeat) cell (one per context) —
cheap enough for a Claude usage-window canary. It is refusal-safe: unparseable/
refused responses are recorded and skipped, never aborting the run.

Providers: local Gemma via Ollama (default), Claude Code CLI (``--provider
claude``, no API key), or OpenAI (``--provider openai``, needs ``OPENAI_API_KEY``).
Outputs go under ``outputs/reputation_league_probe/YYYYMMDD_HHMMSS/``.

    python scripts/probe_reputation_league.py --provider ollama --model gemma3
    python scripts/probe_reputation_league.py --provider claude --model haiku
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

from ultimatum_arena.league.agents import LLMParticipant
from ultimatum_arena.league.prompts import LeagueContext
from ultimatum_arena.league.schemas import GossipRecord, LeagueAgentProfile
from ultimatum_arena.llm.claude_cli_client import ClaudeCLIClient
from ultimatum_arena.llm.client import LLMClient
from ultimatum_arena.llm.errors import (
    ClaudeCLIError,
    LLMError,
    LLMParseError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)
from ultimatum_arena.llm.ollama_client import OllamaLLMClient
from ultimatum_arena.llm.openai_client import OpenAIResponsesClient
from ultimatum_arena.schemas import ResponderObservation

OUTPUT_ROOT = _repo_root / "outputs" / "reputation_league_probe"

# Provider-specific default models, used when --model is not given, so the client,
# printed output, and manifest all record the model actually called.
PROVIDER_DEFAULT_MODELS = {"ollama": "gemma3", "claude": "haiku", "openai": "gpt-5.4-mini"}


def resolve_model(provider: str, model: str | None) -> str:
    """Resolve the effective model: explicit --model wins, else provider default."""
    return model or PROVIDER_DEFAULT_MODELS[provider]


# Fixed economic stimulus: a generous-looking claimed pie, swept offer ratios.
CLAIMED_PIE = 100.0
PIE_RANGE = (50.0, 150.0)
DEFAULT_OFFER_RATIOS = [0.05, 0.12, 0.20, 0.30, 0.45]


def _good_context() -> LeagueContext:
    return LeagueContext(
        opponent_name="Opponent",
        opponent_reputation=92.0,
        memory_summaries=[
            "As proposer, Opponent reported truthfully (claimed 100.0); offered 45.0 (45% of true pie); offer accepted by you.",
            "As proposer, Opponent reported truthfully; offered a fair share last time.",
        ],
        gossip=[
            GossipRecord(
                review_id="g_good", match_id="m", season_index=0, author_id="x",
                target_id="opp", target_role="proposer",
                text="Opponent made a generous, fair-looking offer as proposer.",
                rating=0.8, created_at_match=0,
            )
        ],
        leaderboard_summary="Opponent (900 pts, rep 92)",
    )


def _bad_context() -> LeagueContext:
    return LeagueContext(
        opponent_name="Opponent",
        opponent_reputation=8.0,
        memory_summaries=[
            "As proposer, Opponent underclaimed the pie (claimed 60.0 vs true 100.0) and was caught by audit; offered 18.0 (18% of true pie); offer rejected by you.",
            "As proposer, Opponent lowballed me; offer was stingy.",
        ],
        gossip=[
            GossipRecord(
                review_id="g_bad", match_id="m", season_index=0, author_id="x",
                target_id="opp", target_role="proposer",
                text="Opponent was caught lying about the pie as proposer. Do not trust their claims.",
                rating=-0.9, created_at_match=0,
            )
        ],
        leaderboard_summary="Opponent (950 pts, rep 8)",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Controlled reputation/gossip probe: does opponent standing flip responder decisions?"
    )
    parser.add_argument("--provider", default="ollama", choices=["ollama", "claude", "openai"])
    parser.add_argument(
        "--model",
        default=None,
        help="Model tag. Default depends on provider: ollama=gemma3, claude=haiku, openai=gpt-5.4-mini.",
    )
    parser.add_argument(
        "--responder-mode",
        default="robust",
        choices=["standard", "robust", "naive"],
        help="Responder prompt mode (default: robust).",
    )
    parser.add_argument(
        "--offer-ratios",
        nargs="+",
        type=float,
        default=DEFAULT_OFFER_RATIOS,
        help="Offer / claimed_pie ratios to sweep (default: 0.05 0.12 0.20 0.30 0.45).",
    )
    parser.add_argument("--repeats", default=3, type=int, help="Repeats per cell (default: 3).")
    parser.add_argument("--temperature", default=0.2, type=float, help="Sampling temperature (Ollama/OpenAI).")
    return parser.parse_args(argv)


def _make_client(provider: str, model: str, temperature: float) -> LLMClient:
    if provider == "claude":
        return ClaudeCLIClient(model=model, timeout=180.0)
    if provider == "openai":
        return OpenAIResponsesClient(model=model, temperature=temperature)
    return OllamaLLMClient(model=model, temperature=temperature, timeout=120.0)


def _make_obs(offer_ratio: float) -> ResponderObservation:
    return ResponderObservation(
        claimed_pie=CLAIMED_PIE,
        offer=round(CLAIMED_PIE * offer_ratio, 2),
        public_message="",
        pie_range=PIE_RANGE,
        round_index=0,
        audit_prob=0.25,
        lie_penalty=25.0,
    )


def _decision(participant: LLMParticipant, obs, ctx) -> bool | None:
    """Return True/False for the responder decision, or None on refusal/parse error."""
    try:
        return participant.respond(obs, ctx).accept
    except LLMParseError:
        return None


def run_probe(
    participant: LLMParticipant,
    *,
    offer_ratios: list[float],
    repeats: int,
) -> list[dict]:
    """Return one row per offer ratio comparing good vs bad reputation contexts.

    Each repeat is **paired**: the same fixed observation is shown under the good
    and bad context, so we can report both the acceptance delta
    (``reputation_effect`` = good_accept_rate − bad_accept_rate) AND true paired
    decision flips (``good_only_accepts``: accepted under good but rejected under
    bad on the same repeat; ``bad_only_accepts``; ``same_decision``).
    """
    good_ctx, bad_ctx = _good_context(), _bad_context()
    rows: list[dict] = []
    for ratio in offer_ratios:
        obs = _make_obs(ratio)
        good_accepts = good_valid = good_ref = 0
        bad_accepts = bad_valid = bad_ref = 0
        good_only = bad_only = same = paired = 0
        for _ in range(repeats):
            gd = _decision(participant, obs, good_ctx)
            bd = _decision(participant, obs, bad_ctx)
            if gd is None:
                good_ref += 1
            else:
                good_valid += 1
                good_accepts += int(gd)
            if bd is None:
                bad_ref += 1
            else:
                bad_valid += 1
                bad_accepts += int(bd)
            if gd is not None and bd is not None:
                paired += 1
                if gd and not bd:
                    good_only += 1
                elif bd and not gd:
                    bad_only += 1
                else:
                    same += 1
        good_rate = (good_accepts / good_valid) if good_valid else None
        bad_rate = (bad_accepts / bad_valid) if bad_valid else None
        rows.append(
            {
                "offer_ratio": ratio,
                "offer": obs.offer,
                "claimed_pie": CLAIMED_PIE,
                "good_accept_rate": good_rate,
                "bad_accept_rate": bad_rate,
                "good_refusals": good_ref,
                "bad_refusals": bad_ref,
                # Acceptance delta (not a literal per-repeat flip).
                "reputation_effect": (
                    None if good_rate is None or bad_rate is None else round(good_rate - bad_rate, 3)
                ),
                # True paired decision flips at identical economic terms.
                "paired_repeats": paired,
                "good_only_accepts": good_only,
                "bad_only_accepts": bad_only,
                "same_decision": same,
            }
        )
    return rows


def _print_table(rows: list[dict]) -> None:
    print(
        f"  {'offer_ratio':<13}{'offer':<9}{'good_acc':<10}{'bad_acc':<10}"
        f"{'accept_delta':<14}{'flips(g/b)':<12}"
    )
    print("  " + "-" * 68)
    for r in rows:
        g = "n/a" if r["good_accept_rate"] is None else f"{r['good_accept_rate']:.2f}"
        b = "n/a" if r["bad_accept_rate"] is None else f"{r['bad_accept_rate']:.2f}"
        e = "n/a" if r["reputation_effect"] is None else f"{r['reputation_effect']:+.2f}"
        flips = f"{r['good_only_accepts']}/{r['bad_only_accepts']}"
        print(f"  {r['offer_ratio']:<13}{r['offer']:<9}{g:<10}{b:<10}{e:<14}{flips:<12}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_ROOT / run_id
    effective_model = resolve_model(args.provider, args.model)

    width = 78
    print(f"\n{'=' * width}\n  Controlled Reputation/Gossip Probe (responder-side)\n{'=' * width}")
    print(f"  Provider       : {args.provider}")
    print(f"  Model          : {effective_model}")
    print(f"  Responder mode : {args.responder_mode}")
    print(f"  Offer ratios   : {args.offer_ratios}")
    print(f"  Repeats/cell   : {args.repeats}")
    print(f"  Output dir     : {output_dir.resolve()}")

    client = _make_client(args.provider, effective_model, args.temperature)
    profile = LeagueAgentProfile(
        agent_id="probe", display_name="Probe", kind="llm",
        responder_mode=args.responder_mode, model=effective_model, provider=args.provider,
    )
    participant = LLMParticipant(profile, client, responder_mode=args.responder_mode)

    try:
        rows = run_probe(participant, offer_ratios=args.offer_ratios, repeats=args.repeats)
    except OllamaConnectionError as exc:
        print(f"\nERROR: Cannot connect to Ollama.\n  {exc}\n  -> ollama serve", file=sys.stderr)
        sys.exit(1)
    except OllamaModelNotFoundError as exc:
        print(f"\nERROR: Model not found.\n  {exc}\n  -> ollama pull {effective_model}", file=sys.stderr)
        sys.exit(1)
    except ClaudeCLIError as exc:
        print(f"\nERROR: Claude CLI call failed.\n  {exc}", file=sys.stderr)
        sys.exit(1)
    except LLMError as exc:
        print(f"\nERROR: LLM infrastructure error.\n  {exc}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "results.json").open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    manifest = {
        "experiment": "reputation_league_probe",
        "provider": args.provider,
        "model": effective_model,
        "provider_label": (
            f"Claude Code CLI responder, model tier {effective_model}"
            if args.provider == "claude"
            else f"{args.provider} responder, model {effective_model}"
        ),
        "responder_mode": args.responder_mode,
        "offer_ratios": args.offer_ratios,
        "repeats": args.repeats,
        "claimed_pie": CLAIMED_PIE,
        "temperature": args.temperature if args.provider in ("ollama", "openai") else None,
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'=' * width}\n  Results (acceptance under good vs bad opponent reputation)\n{'=' * width}")
    _print_table(rows)
    effects = [r["reputation_effect"] for r in rows if r["reputation_effect"] is not None]
    if effects:
        print(f"\n  Mean reputation effect (good - bad acceptance): {sum(effects)/len(effects):+.3f}")
        print("  Positive => higher reputation increases acceptance at identical terms.")
    print(f"\n  Output directory: {output_dir.resolve()}\n")


if __name__ == "__main__":
    main()
