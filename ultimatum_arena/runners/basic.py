"""Basic N-round experiment runner."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ultimatum_arena.agents.base import BaseProposer, BaseResponder
from ultimatum_arena.analysis.metrics import compute_metrics
from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
from ultimatum_arena.schemas import RoundResult
from ultimatum_arena.storage.jsonl import append_result, save_summary


def run_experiment(
    proposer: BaseProposer,
    responder: BaseResponder,
    env: HiddenPieAuditEnv,
    n_rounds: int,
    output_dir: Optional[Path | str] = None,
    experiment_name: str = "experiment",
) -> tuple[list[RoundResult], dict]:
    """Run *n_rounds* between *proposer* and *responder* inside *env*.

    Parameters
    ----------
    proposer:
        Any BaseProposer implementation.
    responder:
        Any BaseResponder implementation.
    env:
        A configured HiddenPieAuditEnv instance.
    n_rounds:
        Number of rounds to play.
    output_dir:
        If provided, saves ``{experiment_name}.jsonl`` and
        ``{experiment_name}_summary.json`` inside this directory.
    experiment_name:
        Prefix used for output file names.

    Returns
    -------
    results : list[RoundResult]
    summary : dict  (metrics)
    """
    env.reset()
    results: list[RoundResult] = []

    jsonl_path: Optional[Path] = None
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = output_dir / f"{experiment_name}.jsonl"
        # Overwrite any existing file
        jsonl_path.write_text("", encoding="utf-8")

    for _ in range(n_rounds):
        # 1. Sample pie and build proposer observation
        true_pie, prop_obs = env.proposer_observation()

        # 2. Proposer acts
        prop_action = proposer.act(prop_obs)

        # 3. Build responder observation
        resp_obs = env.responder_observation(prop_action)

        # 4. Responder acts
        resp_action = responder.act(resp_obs)

        # 5. Resolve round
        result = env.step(true_pie, prop_action, resp_action)

        # 6. Attach LLM observability metadata when agents expose it
        metadata: dict = {}
        for prefix, agent in [("proposer", proposer), ("responder", responder)]:
            if hasattr(agent, "last_raw_response"):
                metadata[f"{prefix}_prompt"] = getattr(agent, "last_prompt", "")
                metadata[f"{prefix}_raw_response"] = agent.last_raw_response
                parse_error = getattr(agent, "last_parse_error", None)
                if parse_error is not None:
                    metadata[f"{prefix}_parse_error"] = parse_error
        if metadata:
            result.metadata = metadata

        results.append(result)

        # 7. Notify agents
        proposer.on_round_result(result)
        responder.on_round_result(result)

        # 8. Persist
        if jsonl_path is not None:
            append_result(jsonl_path, result)

    summary = compute_metrics(results)

    if output_dir is not None:
        summary_path = output_dir / f"{experiment_name}_summary.json"
        save_summary(summary_path, summary)

    return results, summary
