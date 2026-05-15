# Stage 4 Prompt: Add Research Analysis Outputs And Plots

You are working on the Python project `ultimatum_arena`.

Goal:
Make the Gemma research sweep outputs easier to analyze by adding stable summary tables and plots.

Important constraints:
- Do not add pandas.
- Use existing `matplotlib` dependency and existing plotting style where possible.
- Do not introduce heavy experiment tracking frameworks.
- Do not rewrite existing metrics.
- Keep plotting optional: if rows are empty, fail with a clear `ValueError`.

Files to inspect:
- `ultimatum_arena/analysis/plots.py`
- `ultimatum_arena/runners/llm_sweep.py`
- `scripts/run_gemma3_research_sweep.py`
- `tests/test_plots.py`
- `tests/test_llm_sweep.py`

Files to create or edit:
- Edit `ultimatum_arena/analysis/plots.py`
- Edit `scripts/run_gemma3_research_sweep.py`
- Add or update tests in `tests/test_plots.py` and/or `tests/test_llm_sweep.py`

Desired analysis outputs:
For each Gemma research sweep, create:

```text
outputs/gemma3_research/YYYYMMDD_HHMMSS/
  combined_summary.csv
  manifest.json
  plots/
    deception_rate_by_audit_prob.png
    proposer_mean_payoff_by_audit_prob.png
    acceptance_rate_by_audit_prob.png
    lie_detection_rate_among_lies_by_audit_prob.png
```

Plot behavior:
- X-axis: `audit_prob`
- Y-axis: selected metric
- Group lines by `strategy`
- If multiple lie penalties are present, either:
  - create one plot per lie penalty, with filenames like `deception_rate_by_audit_prob_penalty_25.png`, or
  - group by both strategy and lie_penalty in the legend.
- Prefer the simpler, readable approach.
- Sort audit probabilities numerically.
- Aggregate across seeds by taking the mean for each plotted cell.

Recommended helper:

```python
def plot_metric_by_audit_prob_for_strategies(
    rows: list[dict],
    metric: str,
    output_path: str | Path,
    *,
    lie_penalty: float | None = None,
) -> None:
    ...
```

or another small helper that fits the current code style.

Table behavior:
- Add an aggregated CSV if useful, for example:

```text
aggregate_by_strategy_audit_penalty.csv
```

Fields:
- `strategy`
- `audit_prob`
- `lie_penalty`
- `n_runs`
- mean of key metrics:
  - `acceptance_rate`
  - `deception_rate`
  - `detected_lie_rate`
  - `lie_detection_rate_among_lies`
  - `proposer_mean_payoff`
  - `responder_mean_payoff`
  - `proposer_advantage`

Use standard library `csv`.

Tests:
- plot function creates a PNG file for simple rows
- aggregation handles multiple seeds
- aggregation groups by strategy/audit/penalty
- empty rows produce clear error
- existing plot tests still pass

Commands to run:

```bash
python -m pytest tests/test_plots.py
python -m pytest tests/test_llm_sweep.py
python -m pytest
```

Optional manual command if Ollama is available:

```powershell
python scripts\run_gemma3_research_sweep.py --preset smoke --model gemma3
```

Definition of done:
- Research sweep outputs include combined CSV, manifest JSON, aggregate CSV, and useful plots.
- Plot/test behavior is deterministic.
- Full test suite passes.

