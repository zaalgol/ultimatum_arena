# Stage 4 Prompt: Analysis Helpers for Adaptive Deception Comparison

You are working on the Python project `ultimatum_arena`.

Goal:
Improve lightweight analysis so we can compare `risk_aware` and `expected_value` adaptation across audit risk.

Important constraints:
- Do not add pandas.
- Do not add heavy statistics dependencies.
- Keep helpers pure and testable.
- Do not require Ollama in tests.
- Keep outputs simple and research-useful.

Files to inspect:
- `ultimatum_arena/analysis/sweep_summary.py`
- `ultimatum_arena/analysis/__init__.py`
- `scripts/run_gemma3_research_sweep.py`
- `tests/test_sweep_summary.py`
- `tests/test_research_sweep_script.py`

Files to edit:
- `ultimatum_arena/analysis/sweep_summary.py`
- `tests/test_sweep_summary.py`
- `scripts/run_gemma3_research_sweep.py` if useful

Required fix:
Make `summarize_strategy_by_audit_risk()` robust to rows loaded from CSV, where numeric values are strings.

Requirements:
- Convert `audit_prob`, `lie_penalty`, and metric values to floats internally.
- `lie_penalty=25.0` should match rows whose `lie_penalty` is `"25.0"`.
- Sorting by `audit_prob` should be numeric.
- Output `audit_prob` should be numeric.
- Add tests with CSV-style string rows.

Optional enhancement:
Add a helper to compare adaptive strategies:

```python
def summarize_adaptive_strategies(
    rows: list[dict],
    strategies: list[str] = ["risk_aware", "expected_value"],
    *,
    lie_penalty: float | None = None,
) -> list[dict]:
    ...
```

Only add this if it stays small. It can simply call `summarize_strategy_by_audit_risk()` for each strategy and concatenate results.

Script integration:
If `expected_value` is present in the sweep rows, print a concise table like:

```text
Expected-value deception by audit probability
audit_prob deception_rate proposer_mean_payoff proposer_advantage
...
```

If both `risk_aware` and `expected_value` are present, it is okay to print two separate tables.

Tests:
- CSV-style string rows work.
- float `lie_penalty` filter matches string row values.
- numeric sorting works when audit probabilities are strings.
- missing/non-numeric values produce clear `ValueError` or are skipped consistently; document the chosen behavior.
- existing tests still pass.

Commands to run:

```bash
python -m pytest tests/test_sweep_summary.py
python -m pytest tests/test_research_sweep_script.py
python -m pytest
```

Definition of done:
- Summary helper works with both in-memory sweep rows and CSV-loaded rows.
- `expected_value` can be summarized by audit risk.
- Full test suite passes.

