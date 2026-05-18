# Stage 3: Add A Fast Expected-Value Probe Script

You are Claude Code working in the `ultimatum_arena` repository.

## Goal

Add a small diagnostic script that runs only a few Gemma rounds for the `expected_value` strategy across two or three audit/penalty conditions. This lets us validate prompt calibration without running the full 144-run `ev` sweep.

## Files To Inspect

- `scripts/run_gemma3_hidden_pie_demo.py`
- `scripts/run_gemma3_research_sweep.py`
- `ultimatum_arena/runners/llm_sweep.py`
- `ultimatum_arena/analysis/sweep_summary.py`
- `tests/test_research_sweep_script.py`

## Files To Create Or Edit

Preferred:

- Create `scripts/probe_gemma3_expected_value.py`
- Add tests in `tests/test_research_sweep_script.py` or a new focused test file if cleaner.

## Expected Behavior

The script should:

- Use local Ollama/Gemma only.
- Require no API keys.
- Run `expected_value` only.
- Use small defaults:
  - `rounds=10`
  - `seeds=[1]`
  - audit/penalty cells:
    - `(audit_prob=0.0, lie_penalty=0.0)`
    - `(audit_prob=0.25, lie_penalty=25.0)`
    - `(audit_prob=1.0, lie_penalty=50.0)`
- Write outputs under `outputs/gemma3_expected_value_probe/<timestamp>/`
- Print a compact table:
  - audit_prob
  - lie_penalty
  - deception_rate
  - acceptance_rate
  - proposer_mean_payoff
  - responder_mean_payoff
- Print the output directory.

It may reuse `run_llm_strategy_sweep()` rather than duplicating runner logic.

## CLI Options

Support at least:

```powershell
python scripts/probe_gemma3_expected_value.py --model gemma3
python scripts/probe_gemma3_expected_value.py --model gemma3 --rounds 5 --seed 1
```

## Tests To Add Or Update

Do not require Ollama in automated tests.

Add tests for:

- argument parsing defaults
- output root default
- configured cells contain low-risk and high-risk cases
- the script can be imported without side effects

If script internals are hard to test, expose small pure helpers like `_probe_cells()` and `_parse_args()`.

## Commands To Run

```powershell
python -m pytest tests/test_research_sweep_script.py
python -m pytest
```

Do not run the live Gemma probe unless asked separately.

## Constraints

- No paid API providers.
- No long sweep in this stage.
- Do not change existing demo script behavior.
- Keep this as a diagnostic research utility, not a new framework.

## Definition Of Done

- A fast expected-value probe script exists.
- Tests cover its pure/config behavior without requiring Ollama.
- Full test suite passes.
