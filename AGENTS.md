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

**`runners/sweep.py`** — `run_audit_penalty_sweep()`: grid over `audit_probabilities × lie_penalties × seeds`, returns metric rows, writes `sweep_summary.csv`.

**`analysis/metrics.py`** — Pure function `compute_metrics(list[RoundResult]) → dict`. 20 keys.

**`analysis/plots.py`** — `plot_metric_by_audit_prob()`: PNG output via matplotlib Agg. Validates all rows.

**`storage/jsonl.py`** — `append_result` / `load_results` (JSONL); `save_summary` (JSON).

**`llm/`** — Phase 2/3 LLM layer: `LLMClient` protocol, `FakeLLMClient`, prompt builders, parser, `LLMProposer`/`LLMResponder`, `OllamaLLMClient`.

## Phase 1 / Phase 2 boundary

**Phase 1** (complete): `envs`, `schemas`, heuristic `agents`, `runners`, `analysis`, `storage`, demo script.

**Phase 2+** (in progress): `ultimatum_arena/llm/`. Keep Phase 2 changes from breaking Phase 1 tests.

## Extending with new agents

Subclass `BaseProposer` or `BaseResponder`, implement `act()`, optionally override `on_round_result()`. Pass to `run_experiment()` — no other changes needed.
