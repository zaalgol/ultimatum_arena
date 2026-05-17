# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Commands

```bash
# Install editable package with dev dependencies
pip install -e ".[dev]"

# Run all tests
python -m pytest

# Run focused test files
python -m pytest tests/test_env.py
python -m pytest tests/test_metrics.py
python -m pytest tests/test_sweep.py
python -m pytest tests/test_ollama_client.py

# Run one test by name
python -m pytest tests/test_env.py::TestLyingProposerDetection::test_lie_detected_with_audit

# Run with coverage
python -m pytest --cov=ultimatum_arena

# Phase 1 demo: heuristic agents only, no API keys or external services
python scripts/run_hidden_pie_demo.py

# Gemma 3 demo: LLM agents via local Ollama (requires ollama pull gemma3)
python scripts/run_gemma3_hidden_pie_demo.py

# Run all three Gemma proposer strategies sequentially
powershell -ExecutionPolicy Bypass -File scripts/run_gemma3_strategy_set.ps1

# Phase 4 research sweep (requires Ollama + gemma3)
python scripts/run_gemma3_research_sweep.py --preset smoke
python scripts/run_gemma3_research_sweep.py --preset research
python scripts/run_gemma3_research_sweep.py --preset risk --model gemma3
python scripts/run_gemma3_research_sweep.py --help

# Optional live Ollama tests, requires Ollama running and gemma3 installed
$env:RUN_OLLAMA_TESTS="1"
python -m pytest tests/test_ollama_client.py
```

## Current State

Phase 1 is complete: Hidden Pie Ultimatum with Audit works as a heuristic-agent research MVP with metrics, sweeps, JSONL/JSON outputs, CSV output, plots, a runnable demo script, and documentation.

Phase 2 is complete: the repository has an LLM layer with a provider-agnostic `LLMClient` protocol, `FakeLLMClient`, LLM-backed agents, prompt builders, JSON parsing, and raw LLM observability metadata in round logs.

Phase 3A is complete: `OllamaLLMClient` runs Gemma 3 locally through Ollama. Paid provider clients and API key handling are not implemented yet.

Phase 4 is in progress: `run_llm_strategy_sweep()` runs a full research grid (strategies × audit_probabilities × lie_penalties × seeds) with LLM agents, writes per-run logs, a combined CSV, an aggregate CSV (means across seeds), a manifest, and strategy plots. `scripts/run_gemma3_research_sweep.py` is the CLI entry point with presets `smoke`, `research`, and `risk`. A fourth LLM proposer strategy `risk_aware` has been added: the model decides whether to report honestly or underclaim based on the expected audit cost (`audit_prob × lie_penalty`). The `--preset risk` sweep compares `honest_fair`, `deceptive`, and `risk_aware` across 4 audit probabilities, 3 penalties, and 3 seeds (108 runs). `summarize_strategy_by_audit_risk()` in `ultimatum_arena.analysis` provides a pure helper to inspect whether `risk_aware` deception falls as audit risk increases.

Local Gemma 3 setup has been verified with Ollama: `gemma3:latest` and `gemma3:4b` are available locally, and `RUN_OLLAMA_TESTS=1 python -m pytest tests/test_ollama_client.py` passes when Ollama is running.

## Architecture

One-shot Hidden Pie Ultimatum rounds flow like this:

```text
HiddenPieAuditEnv.proposer_observation()  -> ProposerObservation (true_pie visible)
BaseProposer.act()                        -> ProposerAction (claimed_pie, offer)
HiddenPieAuditEnv.responder_observation() -> ResponderObservation (claimed_pie only)
BaseResponder.act()                       -> ResponderAction (accept/reject)
HiddenPieAuditEnv.step()                  -> RoundResult
```

`HiddenPieAuditEnv` is the game engine. The proposer privately observes `true_pie`; the responder never receives `true_pie`. Payoffs use the true pie, not the claimed pie. If an audit fires and `claimed_pie != true_pie`, `lie_penalty` is subtracted from proposer payoff even after rejection, so proposer payoff can go negative. `reset()` resets only the round index, not RNG state; use fresh env instances for independent seeded runs.

`schemas/` contains Pydantic records for actions, observations, and results. `ProposerAction` validates `offer <= claimed_pie`.

`agents/base.py` defines the stable synchronous interfaces:

```python
BaseProposer.act(obs: ProposerObservation) -> ProposerAction
BaseResponder.act(obs: ResponderObservation) -> ResponderAction
on_round_result(result: RoundResult) -> None
```

Do not rewrite these interfaces. Future agents should subclass `BaseProposer` or `BaseResponder`.

## Core Modules

- `ultimatum_arena/envs/hidden_pie_audit.py`: Hidden Pie Audit environment.
- `ultimatum_arena/agents/proposers.py`: `HonestFairProposer`, `GreedyHonestProposer`, `LyingGreedyProposer`.
- `ultimatum_arena/agents/responders.py`: `ThresholdResponder`, `SuspiciousResponder`.
- `ultimatum_arena/agents/__init__.py`: public agent exports, including `LLMProposer` and `LLMResponder`.
- `ultimatum_arena/runners/basic.py`: `run_experiment()` for N-round runs. It optionally writes `{experiment_name}.jsonl` and `{experiment_name}_summary.json`.
- `ultimatum_arena/runners/sweep.py`: `run_audit_penalty_sweep()` and `save_sweep_csv()` for heuristic agent grids.
- `ultimatum_arena/runners/llm_sweep.py`: `run_llm_strategy_sweep()` — sweeps strategies × audit_probabilities × lie_penalties × seeds with LLM agents; writes `runs/`, `combined_summary.csv`, and `manifest.json` when `output_dir` is provided. The aggregate CSV and plots are produced by `scripts/run_gemma3_research_sweep.py`, not by the runner itself.
- `ultimatum_arena/analysis/metrics.py`: pure `compute_metrics(list[RoundResult]) -> dict`.
- `ultimatum_arena/analysis/plots.py`: `plot_metric_by_audit_prob()` (group by any field), `plot_metric_by_audit_prob_for_strategies()` (group by strategy, optional lie_penalty filter), `save_aggregate_csv()` (aggregate means by strategy/audit/penalty).
- `ultimatum_arena/analysis/sweep_summary.py`: `summarize_strategy_by_audit_risk(rows, strategy, *, lie_penalty=None)` — pure helper that filters by strategy/penalty, groups by `audit_prob`, averages across seeds, and returns rows sorted by `audit_prob`. Returns `[]` is replaced by raising `ValueError` for no-match; see docstring.
- `ultimatum_arena/storage/jsonl.py`: JSONL/JSON persistence helpers.
- `ultimatum_arena/llm/`: provider-agnostic LLM layer, fake client, parser, prompts, LLM agents, and local Ollama client.
- `scripts/run_gemma3_strategy_set.ps1`: sequentially runs the Gemma demo for `honest_fair`, `self_interested`, and `deceptive` proposer strategies.
- `scripts/run_gemma3_research_sweep.py`: Phase 4 CLI — presets `smoke`, `research`, and `risk`, all dimensions overridable; writes full output tree including plots and aggregate CSV. When `risk_aware` is included, prints an additional deception-by-audit-risk table.

## Phase 1 Demo

Run:

```bash
python scripts/run_hidden_pie_demo.py
```

The demo uses heuristic agents only:

- proposer: `LyingGreedyProposer(claimed_fraction=0.6, offer_fraction=0.4)`
- responder: `ThresholdResponder(min_fraction=0.3)`
- rounds per run: `200`
- audit probabilities: `[0.0, 0.1, 0.25, 0.5, 0.75, 1.0]`
- lie penalties: `[0.0, 10.0, 25.0, 50.0]`
- seeds: `[1, 2, 3]`

Each demo execution creates a timestamped folder:

```text
outputs/hidden_pie_demo/YYYYMMDD_HHMMSS/
```

Inside each run folder:

```text
single_run/single_run.jsonl
single_run/single_run_summary.json
sweep/sweep_summary.csv
sweep/*.jsonl
sweep/*_summary.json
plots/deception_rate_vs_audit_prob.png
plots/proposer_mean_payoff_vs_audit_prob.png
plots/acceptance_rate_vs_audit_prob.png
```

`outputs/` is ignored by `.gitignore`; generated artifacts should not be committed.

## Metrics

`compute_metrics()` returns 12 baseline metrics plus 8 Phase 1 research metrics.

Baseline:

- `n_rounds`
- `acceptance_rate`
- `deception_rate`
- `mean_offer`
- `mean_offer_ratio_true`
- `mean_offer_ratio_claimed`
- `detected_lie_rate`
- `audit_rate`
- `proposer_total_payoff`
- `responder_total_payoff`
- `proposer_mean_payoff`
- `responder_mean_payoff`

Phase 1 research metrics:

- `mean_lie_size`
- `mean_absolute_lie_size`
- `mean_relative_lie_size`
- `mean_offer_gap_from_fair_true_split`
- `mean_offer_gap_from_fair_claimed_split`
- `proposer_advantage`
- `responder_mean_share_of_true_pie`
- `lie_detection_rate_among_lies`

`compute_metrics([])` returns `{}`. Ratio metrics are defensive against zero denominators.

## Sweep API

Use:

```python
from ultimatum_arena.runners import run_audit_penalty_sweep

rows = run_audit_penalty_sweep(
    audit_probabilities=[0.0, 0.25, 0.5, 1.0],
    lie_penalties=[0.0, 10.0, 50.0],
    proposer_factory=...,
    responder_factory=...,
    seeds=[1, 2, 3],
    n_rounds=200,
    output_dir="outputs/example_sweep",
)
```

Factories must return fresh agents per run so stateful agents do not leak state across configurations. The sweep creates a fresh `HiddenPieAuditEnv` per configuration and seed.

## LLM And Ollama

The LLM layer is present but not used by the Phase 1 heuristic demo.

Public LLM pieces:

- `LLMClient` protocol: `generate(prompt: str) -> str`
- `FakeLLMClient`: deterministic test client
- `LLMProposer`, with proposer strategy profiles: `honest_fair`, `self_interested`, `deceptive`, and `risk_aware`
- `LLMResponder`
- `OllamaLLMClient`
- prompt builders and robust JSON extraction/parser

Local Gemma 3 via Ollama:

```bash
ollama pull gemma3
ollama list
```

If `ollama serve` reports port `11434` is already in use, Ollama is already running. Live integration tests can be run with:

```powershell
$env:RUN_OLLAMA_TESTS="1"
python -m pytest tests/test_ollama_client.py
```

The local Ollama tests have been verified against `gemma3`. A Gemma 3 demo script is available at `scripts/run_gemma3_hidden_pie_demo.py`. It runs 3 rounds by default, writes results under `outputs/gemma3_demo/YYYYMMDD_HHMMSS/`, and requires no API keys. Run `python scripts/run_gemma3_hidden_pie_demo.py --help` for all options. Gemma 3 may occasionally return unparsable JSON; rerun or improve prompts in `ultimatum_arena/llm/prompts.py` if needed.

Useful Gemma commands:

```powershell
python scripts/run_gemma3_hidden_pie_demo.py --rounds 50 --strategy honest_fair
python scripts/run_gemma3_hidden_pie_demo.py --rounds 50 --strategy self_interested
python scripts/run_gemma3_hidden_pie_demo.py --rounds 50 --strategy deceptive
powershell -ExecutionPolicy Bypass -File scripts/run_gemma3_strategy_set.ps1
```

The strategy-set script stops on the first failed run. If `ollama serve` reports that port `11434` is already in use, Ollama is already running. Verify it with `Invoke-RestMethod http://localhost:11434/api/tags`.

The Gemma demo uses:

- `OllamaLLMClient(model="gemma3")`
- `LLMProposer`
- `LLMResponder`
- `HiddenPieAuditEnv`
- `run_experiment`

Default Gemma demo settings are intentionally small: 3 rounds, `audit_prob=0.25`, `lie_penalty=25.0`, `rng_seed=42`, and `temperature=0.2`.

Recent Gemma strategy runs show the expected Hidden Pie + Audit mechanism:

- `honest_fair`: truthful claims, high acceptance, no deception.
- `self_interested`: truthful claims, lower/more variable offers, no deception.
- `deceptive`: frequent underclaims, offers near half of the claimed pie, high acceptance, and audit-driven lie detection around the configured audit rate.

## Phase Boundaries

Phase 1 (complete):

- Complete heuristic research MVP.
- No API keys.
- No external services.
- No real LLM calls in the default demo.

Phase 2 (complete):

- Provider-agnostic LLM architecture.
- Fake client first.
- Prompt builders and robust JSON parsing.
- LLM proposer/responder agents with raw prompt/response metadata.

Phase 3A (complete):

- Local Ollama/Gemma 3 support.
- No API keys.
- Gemma proposer strategy profiles and sequential local strategy runner.

Phase 4 (starting):

- `run_llm_strategy_sweep()` for systematic multi-strategy experiments.
- `run_gemma3_research_sweep.py` CLI with smoke and research presets.
- Aggregate CSV and strategy plots from sweep outputs.
- No paid providers. No async. No database.

Later provider phases:

- OpenAI/Anthropic-compatible clients.
- API key handling.
- Paid model comparison experiments.

Do not add paid providers, API key handling, async architecture, databases, web UI, notebooks as primary execution path, or advanced game variants unless explicitly requested.

## Coding Guidance

- Keep the existing architecture incremental.
- Do not rewrite `HiddenPieAuditEnv`, `BaseProposer`, `BaseResponder`, or `run_experiment` unless fixing a concrete bug.
- Keep `compute_metrics()` pure.
- Use factories for sweep agents.
- Keep tests focused and run `python -m pytest` before handoff.
- Treat generated files under `outputs/` as runtime artifacts, not source.

## Claude Hook Behavior

`.claude/settings.local.json` contains a `PostToolUse` hook for `Write|Edit`. It should assess whether `CLAUDE.md` needs updating after architecture-relevant edits, including:

- Python source/tests/scripts (`*.py`)
- Markdown docs (`*.md`)
- project/config files (`*.toml`, `*.json`)
- `.gitignore`
- files under `scripts/` or `.claude/`

It intentionally skips `CLAUDE.md` itself to avoid update loops and ignores generated/noisy paths such as `outputs/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/`, `dist/`, and `build/`.

The same settings file also contains an async review-agent hook for edited source/config/doc files. It skips generated paths and `.claude/` settings files, then checks for concrete bugs, security issues, code-quality problems, and architecture drift. If it finds issues, it rewakes the session with a short review; otherwise it stays silent.
