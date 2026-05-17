# Stage 4 Prompt: Add Risk-Aware Analysis Checks

You are working on the Python project `ultimatum_arena`.

Goal:
Add lightweight analysis support for interpreting whether `risk_aware` responds to audit risk.

Important constraints:
- Do not add pandas.
- Do not add heavy statistics dependencies.
- Do not overbuild analysis.
- Keep functions pure and testable.
- Do not require Ollama in tests.

Files to inspect:
- `ultimatum_arena/analysis/metrics.py`
- `ultimatum_arena/analysis/plots.py`
- `scripts/run_gemma3_research_sweep.py`
- `tests/test_plots.py`
- `tests/test_metrics.py`

Files to edit:
- Prefer editing `ultimatum_arena/analysis/plots.py` only if the helper naturally belongs there.
- Alternatively create a small new module:
  - `ultimatum_arena/analysis/sweep_summary.py`
- Update `ultimatum_arena/analysis/__init__.py` if adding stable public helpers.
- Add tests.

Desired helper:
Add a small pure helper that summarizes deception/payoff trends for one strategy across audit risk.

Example:

```python
def summarize_strategy_by_audit_risk(
    rows: list[dict],
    strategy: str,
    *,
    lie_penalty: float | None = None,
) -> list[dict]:
    ...
```

Expected behavior:
- Filter rows by strategy.
- Optionally filter by lie penalty.
- Group by `audit_prob`.
- Average across seeds and penalties if not filtered.
- Return rows sorted by `audit_prob`.
- Include:
  - `strategy`
  - `audit_prob`
  - `n_runs`
  - `deception_rate`
  - `proposer_mean_payoff`
  - `proposer_advantage`
  - `lie_detection_rate_among_lies`

This helper should make it easy to inspect whether `risk_aware` deception falls as audit risk increases.

Tests:
- grouping by audit probability works
- rows are sorted numerically
- multiple seeds are averaged
- lie penalty filter works
- empty matching rows returns `[]` or raises `ValueError`; choose one behavior and document it
- no Ollama required

Optional script integration:
If simple, have `scripts/run_gemma3_research_sweep.py` print an additional short table when `risk_aware` is present:

```text
Risk-aware deception by audit probability
audit_prob deception_rate proposer_mean_payoff proposer_advantage
...
```

Commands to run:

```bash
python -m pytest tests/test_plots.py tests/test_metrics.py
python -m pytest
```

Definition of done:
- There is a small tested way to summarize `risk_aware` behavior by audit risk.
- Existing plots and sweep outputs still work.
- Full test suite passes.

