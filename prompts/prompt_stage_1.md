# Stage 1: Audit Expected-Value Behavior And Design Calibration

You are Claude Code working in the `ultimatum_arena` repository.

## Goal

Audit why the current Gemma `expected_value` strategy produced zero deception and highly generous offers in the completed run:

`outputs/gemma3_research/20260518_004953`

Do not make implementation changes in this stage. Produce a short technical diagnosis and an implementation plan for the next stage.

## Files To Inspect

- `ultimatum_arena/llm/prompts.py`
- `ultimatum_arena/agents/llm_agents.py`
- `ultimatum_arena/runners/llm_sweep.py`
- `scripts/run_gemma3_research_sweep.py`
- `tests/test_llm_agents.py`
- `tests/test_research_sweep_script.py`
- `outputs/gemma3_research/20260518_004953/combined_summary.csv`
- `outputs/gemma3_research/20260518_004953/aggregate_by_strategy_audit_penalty.csv`
- Several representative JSONL files in `outputs/gemma3_research/20260518_004953/runs/`, especially:
  - `*strategy-expected-value_audit-0p000_penalty-0p000_seed-1.jsonl`
  - `*strategy-deceptive_audit-0p000_penalty-0p000_seed-1.jsonl`
  - `*strategy-risk-aware_audit-0p000_penalty-0p000_seed-1.jsonl`

## What To Analyze

- Whether the zero deception for `expected_value` is a logging/metrics bug or real model behavior.
- Whether the prompt gives Gemma enough concrete numerical guidance to choose deception when audit cost is zero.
- Whether responder behavior makes deceptive offers acceptable.
- Whether the next change should revise `expected_value` or add a separate strategy name.

## Constraints

- Do not edit code or docs in this stage.
- Do not run a new long Gemma sweep.
- Do not add Phase 5 game variants.
- Do not add paid API providers.

## Commands To Run

Run only lightweight read/inspection commands. Recommended:

```powershell
python -m pytest tests/test_llm_agents.py tests/test_research_sweep_script.py tests/test_sweep_summary.py
```

Optionally use small Python snippets to summarize the existing CSV/JSONL outputs.

## Definition Of Done

- Provide a concise diagnosis.
- Recommend the exact strategy calibration for Stage 2.
- Confirm whether the current implementation pipeline is working and whether the problem is prompt behavior.
