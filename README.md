# ultimatum_arena

A Python research framework for studying deception in ultimatum games with an audit mechanism. Agents can misreport the pie size, and an auditor fires with configurable probability to penalise lies.

---

## What is the Hidden Pie Ultimatum Game with Audit?

A standard ultimatum game has two players split a known sum. This variant adds **information asymmetry** and **auditing**:

- The **proposer** privately observes the true pie size.
- The proposer may report a *different* claimed pie size to the responder, pocketing the hidden surplus.
- The **responder** sees only the claimed pie and the offer, and decides to accept or reject.
- Payoffs are always computed from the **true** pie, so lying benefits the proposer only if undetected.
- After each round, an **audit** fires with probability `audit_prob`. If the proposer lied and the audit fires, `lie_penalty` is subtracted from the proposer's payoff—even on rejection, so the payoff can go negative.

This creates a tension between deception gains and audit risk that is the core object of study.

---

## Research Motivation

Standard game theory predicts honest behaviour when audit probability × penalty exceeds the deception gain. Real agents—human or AI—may deviate from this prediction. The framework lets researchers:

- Measure deception rates, detection rates, and offer fairness across audit/penalty regimes.
- Compare heuristic baselines against LLM-backed agents.
- Run reproducible parameter sweeps and export results to CSV for downstream analysis.

---

## Installation

```bash
git clone <repo>
cd ultimatum_arena
pip install -e ".[dev]"
```

Requires Python 3.11+. Runtime dependencies: `pydantic>=2.0`, `matplotlib>=3.7`.

---

## Quick Start

```bash
# Run all tests
python -m pytest

# Run the Phase 1 demo (heuristic agents, full sweep, plots)
python scripts/run_hidden_pie_demo.py

# Run the Gemma 3 demo (LLM agents via local Ollama)
ollama pull gemma3
python scripts/run_gemma3_hidden_pie_demo.py

# Run all three Gemma proposer strategies sequentially
powershell -ExecutionPolicy Bypass -File scripts/run_gemma3_strategy_set.ps1

# Fast expected-value calibration probe (3 audit/penalty cells, ~3 minutes)
python scripts/probe_gemma3_expected_value.py --model gemma3

# Full four-strategy research sweep (144 runs, ~2 hours on Gemma 3)
python scripts/run_gemma3_research_sweep.py --preset ev --model gemma3
```

The Phase 1 demo writes to a new timestamped folder under `outputs/hidden_pie_demo/YYYYMMDD_HHMMSS/`.

---

## Demo Outputs

Each execution creates `outputs/hidden_pie_demo/<YYYYMMDD_HHMMSS>/` and writes:

| Path (relative to run folder) | Contents |
|---|---|
| `single_run/single_run.jsonl` | One JSON line per round |
| `single_run/single_run_summary.json` | Aggregated metrics for the run |
| `sweep/sweep_summary.csv` | One row per (audit_prob, lie_penalty, seed) cell |
| `sweep/*.jsonl` | Per-cell round logs |
| `plots/*.png` | Metric vs audit_prob plots grouped by lie_penalty |

Running the script twice produces two separate timestamped folders; old outputs are never deleted.

---

## Run Local Gemma 3 Demo

Prerequisites:

```bash
ollama pull gemma3   # download the local Gemma model
# Ollama must be running (ollama serve, or it may already be running as a service)
```

Run:

```bash
python scripts/run_gemma3_hidden_pie_demo.py
```

Outputs are written to `outputs/gemma3_demo/YYYYMMDD_HHMMSS/`:

| File | Contents |
|---|---|
| `gemma3_vs_gemma3.jsonl` | One JSON line per round |
| `gemma3_vs_gemma3_summary.json` | Aggregated metrics |

No API key required. Defaults: 3 rounds, temperature 0.2, audit_prob 0.25, lie_penalty 25.

The Gemma proposer supports explicit strategy profiles:

| Strategy | Meaning |
|---|---|
| `honest_fair` | Reports the true pie and aims for fair, high-acceptance offers |
| `self_interested` | Reports the true pie but tries to keep more payoff while still being accepted |
| `deceptive` | Instruction-driven lying baseline: underclaims the true pie (~60–70%) and offers ~50% of the claimed pie, accepting audit risk regardless of conditions |
| `risk_aware` | Cautious incentive-aware strategy: told to weigh expected audit cost (`audit_prob × lie_penalty`) against the underclaiming surplus; in practice may avoid lying even at low penalty — conservative baseline |
| `expected_value` | Prompt-calibrated numeric payoff maximizer: given a worked example and explicit decision rule, underclaims (~55–65% of true pie) when expected audit cost is zero and should adapt at higher audit risk; uses `audit_prob × lie_penalty` as the cost term |

Optional commands:

```bash
python scripts/run_gemma3_hidden_pie_demo.py --model gemma3 --rounds 5 --temperature 0.3
python scripts/run_gemma3_hidden_pie_demo.py --rounds 50 --strategy deceptive
python scripts/run_gemma3_hidden_pie_demo.py --help
```

To run the three strategy profiles one after another:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_gemma3_strategy_set.ps1
```

The strategy-set script stops on the first failed run. If Ollama is already running, `ollama serve` may report that port `11434` is in use; that is expected. Verify the local API with:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags
```

> **Note:** Gemma 3 may occasionally return unparsable JSON. If this happens the script exits with a clear error. Rerun or improve the prompts in `ultimatum_arena/llm/prompts.py`.

---

## Research Sweep (Phase 4)

The research sweep runs a full grid of strategies × audit probabilities × lie penalties × seeds and produces analysis-ready outputs.

```bash
# Quick smoke test: 2 strategies × 3 audit probs × 2 penalties × 1 seed = 6 runs, 10 rounds each
python scripts/run_gemma3_research_sweep.py --preset smoke

# Full research sweep: 3 strategies × 6 audit probs × 4 penalties × 3 seeds = 216 runs, 50 rounds each
python scripts/run_gemma3_research_sweep.py --preset research

# Risk-aware comparison: honest_fair vs deceptive vs risk_aware across audit risk
# 3 strategies × 4 audit probs × 3 penalties × 3 seeds = 108 runs, 50 rounds each
python scripts/run_gemma3_research_sweep.py --preset risk --model gemma3

# Expected-value comparison: four proposer strategies
# 4 strategies × 4 audit probs × 3 penalties × 3 seeds = 144 runs, 50 rounds each
python scripts/run_gemma3_research_sweep.py --preset ev --model gemma3

# Override individual dimensions
python scripts/run_gemma3_research_sweep.py --preset smoke --rounds 20 --seeds 1 2 3
python scripts/run_gemma3_research_sweep.py --preset ev --rounds 10 --seeds 1 --audit-probs 0.0 1.0 --lie-penalties 0 50

# See all options
python scripts/run_gemma3_research_sweep.py --help
```

Outputs are written to `outputs/gemma3_research/YYYYMMDD_HHMMSS/`:

| Path | Contents |
|---|---|
| `runs/<run>.jsonl` | Per-round logs for each cell |
| `runs/<run>_summary.json` | Per-cell metrics |
| `combined_summary.csv` | One row per (strategy, audit_prob, lie_penalty, seed) |
| `aggregate_by_strategy_audit_penalty.csv` | Means across seeds, grouped by (strategy, audit_prob, lie_penalty) |
| `manifest.json` | Sweep configuration |
| `plots/deception_rate_by_audit_prob.png` | Deception rate vs audit probability, lines by strategy |
| `plots/proposer_mean_payoff_by_audit_prob.png` | Proposer payoff vs audit probability |
| `plots/acceptance_rate_by_audit_prob.png` | Acceptance rate vs audit probability |
| `plots/lie_detection_rate_among_lies_by_audit_prob.png` | Lie detection rate vs audit probability |

### Interpreting results

- **`deceptive` strategy** is instruction-driven: the model is told to underreport (~60–70% of true pie) regardless of incentives. It shows near-100% `deception_rate` across all audit/penalty conditions.
- **`risk_aware` strategy** is cautious and incentive-aware: it is told to weigh expected audit cost against the underclaiming surplus, but in practice may avoid lying even at low penalty — use as a conservative baseline.
- **`expected_value` strategy** is a prompt-calibrated numeric maximizer: a worked example and explicit `IF/ELSE` decision rule instruct the model to compare honest vs underclaiming options using `expected audit cost = audit_prob × lie_penalty`. In probe runs with Gemma 3 the strategy reliably underclaims at zero audit cost (`deception_rate = 1.0`), and proposer payoff degrades predictably as penalties rise. Whether it reliably switches to honest behaviour at high audit risk depends on the model; Gemma 3 tends to keep lying but incurs heavy penalties.
- **Fast calibration probe**: `probe_gemma3_expected_value.py` runs 10 rounds across three audit/penalty cells (zero risk, moderate, maximum) and prints a compact table. Use this to validate prompt behaviour before committing to a full sweep. Outputs go to `outputs/gemma3_expected_value_probe/<timestamp>/`.
- **`honest_fair`** and **`self_interested`** should show near-zero `deception_rate` regardless of penalty regime.
- **`lie_detection_rate_among_lies`** should track closely with `audit_prob` (audits are the only detection mechanism).
- Single-run results are noisy; use the aggregate CSV to compare across seeds.
- When `risk_aware` or `expected_value` is included in a sweep, the script prints a per-strategy deception-by-audit-prob table.
- Use `summarize_strategy_by_audit_risk(rows, "expected_value")` or `summarize_adaptive_strategies(rows)` from `ultimatum_arena.analysis` to inspect trends programmatically. Both helpers accept in-memory rows or CSV-loaded string rows.


---

## Python API

```python
from ultimatum_arena.envs import HiddenPieAuditEnv
from ultimatum_arena.agents import LyingGreedyProposer, ThresholdResponder
from ultimatum_arena.runners import run_experiment, run_audit_penalty_sweep
from ultimatum_arena.analysis import compute_metrics, plot_metric_by_audit_prob

# Single experiment
env = HiddenPieAuditEnv(pie_range=(50, 150), audit_prob=0.25, lie_penalty=10.0, rng_seed=42)
results, metrics = run_experiment(
    LyingGreedyProposer(), ThresholdResponder(), env, n_rounds=200,
    output_dir="outputs/myrun", experiment_name="demo",
)

# Heuristic parameter sweep
rows = run_audit_penalty_sweep(
    audit_probabilities=[0.0, 0.25, 0.5, 1.0],
    lie_penalties=[0.0, 10.0, 50.0],
    proposer_factory=LyingGreedyProposer,
    responder_factory=ThresholdResponder,
    seeds=[1, 2, 3],
    n_rounds=200,
    output_dir="outputs/sweep",
)

# LLM strategy sweep (Ollama/Gemma or any LLMClient)
from ultimatum_arena.runners import run_llm_strategy_sweep
from ultimatum_arena.llm.ollama_client import OllamaLLMClient

rows = run_llm_strategy_sweep(
    proposer_client_factory=lambda: OllamaLLMClient(model="gemma3"),
    responder_client_factory=lambda: OllamaLLMClient(model="gemma3"),
    strategies=["honest_fair", "self_interested", "deceptive"],
    audit_probabilities=[0.0, 0.25, 0.5, 1.0],
    lie_penalties=[0.0, 25.0],
    seeds=[1, 2, 3],
    n_rounds=50,
    output_dir="outputs/llm_sweep",
)

# Plot and aggregate analysis
from ultimatum_arena.analysis import (
    plot_metric_by_audit_prob,
    plot_metric_by_audit_prob_for_strategies,
    save_aggregate_csv,
)

plot_metric_by_audit_prob(rows, "deception_rate", "outputs/plots/deception.png")
plot_metric_by_audit_prob_for_strategies(rows, "deception_rate", "outputs/plots/deception_by_strategy.png")
save_aggregate_csv(rows, "outputs/aggregate.csv")
```

---

## Metrics Reference

### Baseline metrics

| Key | Description |
|---|---|
| `n_rounds` | Total rounds played |
| `acceptance_rate` | Fraction of rounds the responder accepted |
| `deception_rate` | Fraction of rounds where `claimed_pie != true_pie` |
| `mean_offer` | Mean absolute offer |
| `mean_offer_ratio_true` | Mean `offer / true_pie` |
| `mean_offer_ratio_claimed` | Mean `offer / claimed_pie` |
| `detected_lie_rate` | Fraction of rounds where `lie_detected` is True |
| `audit_rate` | Fraction of rounds where an audit occurred |
| `proposer_total_payoff` | Sum of proposer payoffs |
| `responder_total_payoff` | Sum of responder payoffs |
| `proposer_mean_payoff` | Mean proposer payoff per round |
| `responder_mean_payoff` | Mean responder payoff per round |

### Phase 1 research metrics

| Key | Description |
|---|---|
| `mean_lie_size` | Mean `true_pie − claimed_pie`; positive = understatement |
| `mean_absolute_lie_size` | Mean `|true_pie − claimed_pie|` |
| `mean_relative_lie_size` | Mean `(true_pie − claimed_pie) / true_pie` |
| `mean_offer_gap_from_fair_true_split` | Mean `|offer − true_pie / 2|` |
| `mean_offer_gap_from_fair_claimed_split` | Mean `|offer − claimed_pie / 2|` |
| `proposer_advantage` | `proposer_mean_payoff − responder_mean_payoff` |
| `responder_mean_share_of_true_pie` | Mean `responder_payoff / true_pie` |
| `lie_detection_rate_among_lies` | Detected deceptive rounds / all deceptive rounds; 0.0 if no deception |

---

## Heuristic Agents

| Class | Role | Behaviour |
|---|---|---|
| `HonestFairProposer` | Proposer | Reports true pie; offers half |
| `GreedyHonestProposer(offer_fraction)` | Proposer | Reports true pie; offers a small fraction |
| `LyingGreedyProposer(claimed_fraction, offer_fraction)` | Proposer | Understates pie; offers a fraction of the lie |
| `ThresholdResponder(min_fraction)` | Responder | Accepts if `offer >= min_fraction * claimed_pie` |
| `SuspiciousResponder(min_fraction, suspicion_discount)` | Responder | Discounts the claimed pie before thresholding |

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| **Phase 1** | Complete | Hidden Pie Audit game, heuristic agents, sweep runner, CSV/JSON output, matplotlib plots |
| **Phase 2** | Complete | LLM agent infrastructure: `LLMClient` protocol, `FakeLLMClient` for tests, prompt builders, response parser, `LLMProposer`/`LLMResponder` |
| **Phase 3A** | Complete | Local Ollama/Gemma support through `OllamaLLMClient`; no API keys required |
| **Phase 3B** | Planned | Paid provider clients such as OpenAI-compatible and Anthropic-compatible clients |
| **Phase 4** | Starting | Systematic multi-strategy research sweeps: `run_llm_strategy_sweep`, aggregate CSV, strategy plots |
| **Phase 5** | Planned | Multi-model comparison; head-to-head proposer vs responder matchups; adversarial prompting benchmarks |

---

## Project Structure

```
ultimatum_arena/
  agents/       BaseProposer, BaseResponder, heuristic agents, LLM agents
  envs/         HiddenPieAuditEnv
  schemas/      ProposerAction, ResponderAction, RoundResult, observations
  runners/      run_experiment, run_audit_penalty_sweep, run_llm_strategy_sweep, save_sweep_csv
  analysis/     compute_metrics, plot_metric_by_audit_prob, plot_metric_by_audit_prob_for_strategies,
                save_aggregate_csv
  storage/      JSONL + JSON persistence helpers
  llm/          LLMClient protocol, FakeLLMClient, OllamaLLMClient, prompts, parser
scripts/
  run_hidden_pie_demo.py            Phase 1 end-to-end demo (heuristic agents)
  run_gemma3_hidden_pie_demo.py     Single-run Gemma 3 demo
  run_gemma3_strategy_set.ps1       Sequential strategy comparison (PowerShell)
  run_gemma3_research_sweep.py      Phase 4 full research sweep with presets
  probe_gemma3_expected_value.py    Fast expected-value calibration probe (3 cells, ~3 min)
outputs/                           Runtime artifacts (gitignored)
  hidden_pie_demo/                 Heuristic demo outputs
  gemma3_demo/                     Single Gemma demo outputs
  gemma3_research/                 Research sweep outputs
  gemma3_expected_value_probe/     Expected-value probe outputs
tests/                             Unit tests (2 live-Ollama integration tests skipped by default)
```

---

## Claude Automation

The repository includes `.claude/settings.local.json` hooks for Claude Code:

- a `CLAUDE.md` maintenance hook that checks whether architecture guidance needs updating after source, test, script, doc, or config edits
- a focused review hook that inspects edited source/config/doc files for concrete bugs, security issues, quality issues, and architecture drift

The hooks intentionally ignore generated artifacts under `outputs/`, caches, build directories, and `.claude/` settings files to avoid review/update loops.
