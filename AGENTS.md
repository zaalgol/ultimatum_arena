# AGENTS.md

Guidance for AI coding agents (Codex, etc.) working in this repository.

## Commands

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run all tests
python -m pytest

# Run a single test file
python -m pytest tests/test_env.py

# Run a single test by name
python -m pytest tests/test_env.py::TestLyingProposerDetection::test_lie_detected_with_audit

# Run with coverage
python -m pytest --cov=ultimatum_arena

# Phase 1 demo (heuristic agents, sweep, plots — no API keys needed)
python scripts/run_hidden_pie_demo.py

# Gemma 3 demo (LLM agents via local Ollama — requires ollama pull gemma3)
python scripts/run_gemma3_hidden_pie_demo.py

# Run all three Gemma proposer strategies sequentially
powershell -ExecutionPolicy Bypass -File scripts/run_gemma3_strategy_set.ps1

# Phase 4 research sweep (requires Ollama + gemma3)
python scripts/run_gemma3_research_sweep.py --preset smoke
python scripts/run_gemma3_research_sweep.py --preset research
python scripts/run_gemma3_research_sweep.py --preset risk --model gemma3
python scripts/run_gemma3_research_sweep.py --preset ev --model gemma3
python scripts/run_gemma3_research_sweep.py --help

# Fast expected-value calibration probe (3 cells, no long sweep needed)
python scripts/probe_gemma3_expected_value.py --model gemma3
python scripts/probe_gemma3_expected_value.py --model gemma3 --rounds 5 --seed 1
```

## Architecture

One-shot ultimatum game where the proposer privately knows the true pie size and may misreport it. Per-round data flow:

```
HiddenPieAuditEnv.proposer_observation()  →  ProposerObservation (true_pie visible)
  → BaseProposer.act()                    →  ProposerAction (claimed_pie, offer)
HiddenPieAuditEnv.responder_observation() →  ResponderObservation (claimed_pie only)
  → BaseResponder.act()                   →  ResponderAction (accept/reject)
HiddenPieAuditEnv.step()                  →  RoundResult
```

**`envs/hidden_pie_audit.py`** — Game engine. Payoffs use `true_pie`; `lie_penalty` is subtracted on audit fire even if rejected. `reset()` resets round index only, not the RNG.

**`schemas/`** — `actions.py`, `observations.py`, `results.py`. `ProposerAction` validates `offer <= claimed_pie`.

**`agents/base.py`** — `BaseProposer` / `BaseResponder` ABCs. `act()` required; `on_round_result()` optional for stateful agents.

**`runners/basic.py`** — `run_experiment()`: N rounds, notifies agents, optionally writes `{name}.jsonl` + `{name}_summary.json`.

**`runners/sweep.py`** — `run_audit_penalty_sweep()`: heuristic grid over `audit_probabilities × lie_penalties × seeds`, returns metric rows, writes `sweep_summary.csv`.

**`runners/llm_sweep.py`** — `run_llm_strategy_sweep()`: LLM grid over `strategies × audit_probabilities × lie_penalties × seeds`. Calls `proposer_client_factory` and `responder_client_factory` once per cell. Writes per-run logs under `runs/`, `combined_summary.csv`, `manifest.json`; `save_aggregate_csv` and plots are called by the script.

**`analysis/metrics.py`** — Pure function `compute_metrics(list[RoundResult]) → dict`. 20 keys.

**`analysis/plots.py`** — `plot_metric_by_audit_prob()`: PNG via matplotlib Agg, group by any field. `plot_metric_by_audit_prob_for_strategies()`: convenience wrapper grouping by strategy with optional lie_penalty filter. `save_aggregate_csv()`: means by (strategy, audit_prob, lie_penalty).

**`analysis/sweep_summary.py`** — `summarize_strategy_by_audit_risk(rows, strategy, *, lie_penalty=None)`: pure helper; filters by strategy and optional penalty, groups by `audit_prob`, averages across seeds, returns rows sorted by `audit_prob`; raises `ValueError` when no rows match. `summarize_adaptive_strategies(rows, strategies, *, lie_penalty=None)`: calls the above for multiple strategies, concatenates results, skips missing strategies silently. Both helpers coerce numeric fields from strings for CSV compatibility.

**`storage/jsonl.py`** — `append_result` / `load_results` (JSONL); `save_summary` (JSON).

**`llm/`** — Phase 2/3 LLM layer: `LLMClient` protocol, `FakeLLMClient`, prompt builders, parser, `LLMProposer`/`LLMResponder`, `OllamaLLMClient`. `LLMProposer` accepts five strategies: `honest_fair`, `self_interested`, `deceptive`, `risk_aware`, `expected_value`.

## Phase boundaries

**Phase 1** (complete): `envs`, `schemas`, heuristic `agents`, `runners`, `analysis`, `storage`, demo script.

**Phase 2** (complete): `ultimatum_arena/llm/` — LLM agent infrastructure, fake client, prompts, parser.

**Phase 3A** (complete): `OllamaLLMClient`, Gemma strategy profiles, `run_gemma3_hidden_pie_demo.py`, `run_gemma3_strategy_set.ps1`.

**Phase 4** (in progress): `run_llm_strategy_sweep()`, `run_gemma3_research_sweep.py` with presets `smoke`, `research`, `risk`, `ev`, aggregate CSV, strategy plots. Five LLM strategies available. Analysis helpers: `summarize_strategy_by_audit_risk()` and `summarize_adaptive_strategies()`.
- `deceptive` = instruction-driven lying baseline; always underclaims (~60–70% of true pie) regardless of audit risk.
- `risk_aware` = cautious/incentive-aware; told to weigh expected audit cost; in practice may avoid lying even at zero penalty.
- `expected_value` = prompt-calibrated numeric maximizer; uses a worked example and explicit `IF/ELSE` rule; reliably underclaims at zero audit cost (Gemma 3 probe: `deception_rate = 1.0`); may not switch to honest at high audit risk on small models.
- `probe_gemma3_expected_value.py` = fast 3-cell calibration check; run before committing to the 144-run `ev` sweep. Outputs under `outputs/gemma3_expected_value_probe/`.
- Use `--preset ev` to compare four proposer strategies (144 runs). Outputs under `outputs/gemma3_research/`.
- Still local Ollama/Gemma only; no paid provider clients.

## Extending with new agents

Subclass `BaseProposer` or `BaseResponder`, implement `act()`, optionally override `on_round_result()`. Pass to `run_experiment()` — no other changes needed.
