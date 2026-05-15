# Code Review: Research-Grade Gemma Sweep Implementation

## Findings

### P2: Strategy plots average away the lie-penalty dimension

Files:
- `scripts/run_gemma3_research_sweep.py:306-320`
- `ultimatum_arena/analysis/plots.py:127-162`

The research sweep varies both `audit_prob` and `lie_penalty`, but the script generates only one plot per metric by calling `plot_metric_by_audit_prob_for_strategies(rows, metric, ...)` without a `lie_penalty` filter. The helper then groups only by `strategy`, so duplicate `(strategy, audit_prob)` cells are averaged across all lie penalties and seeds.

That makes the key research question harder to answer and can produce misleading plots. For example, deception at `lie_penalty=0` and `lie_penalty=50` may be collapsed into one line, hiding exactly the penalty effect the sweep is designed to measure.

Recommendation:
Generate plots per lie penalty, for example:

```text
plots/deception_rate_by_audit_prob_penalty_0.png
plots/deception_rate_by_audit_prob_penalty_10.png
plots/deception_rate_by_audit_prob_penalty_25.png
plots/deception_rate_by_audit_prob_penalty_50.png
```

or include both strategy and lie penalty in the plotted group label. The aggregate CSV already preserves `(strategy, audit_prob, lie_penalty)`, so the plot layer should preserve it too.

### P2: Manifest is missing model, temperature, preset, and run metadata

File:
- `ultimatum_arena/runners/llm_sweep.py:156-166`

`manifest.json` records sweep dimensions, but it does not record the LLM model, temperature, selected CLI preset, script entry point, or run timestamp. These values matter for reproducing research runs, especially because `combined_summary.csv` may be moved or filtered independently later.

The combined CSV rows include `model` and `temperature`, but the manifest should still describe the run as a whole. Right now a reader opening only `manifest.json` cannot tell whether a run used `gemma3`, another Ollama model, or which preset created it.

Recommendation:
Allow `run_llm_strategy_sweep()` to accept optional `manifest_extra: dict | None`, or have `scripts/run_gemma3_research_sweep.py` update/write the manifest after the sweep. Include at least:

```text
model
temperature
preset
run_id
created_at
script
output_dir
```

### P2: Plot generation failures are silently swallowed

File:
- `scripts/run_gemma3_research_sweep.py:314-322`

The script catches `ValueError` and `KeyError` during plot generation and silently continues. It then prints the plots directory as if plots were produced. This can hide real analysis-output failures, such as a metric typo, missing field, malformed rows, or a future plotting regression.

Recommendation:
Do not silently pass. Either:

- let the exception fail the script, or
- collect skipped plot errors and print a warning listing the metric and error.

For research workflows, silent missing plots are worse than a loud failure.

### P3: CLAUDE.md overstates what `run_llm_strategy_sweep()` writes

File:
- `CLAUDE.md:91`

`CLAUDE.md` says `ultimatum_arena/runners/llm_sweep.py` writes `aggregate_by_strategy_audit_penalty.csv` and `plots/` when `output_dir` is provided. The actual runner writes only:

```text
runs/
combined_summary.csv
manifest.json
```

The aggregate CSV and plots are created by `scripts/run_gemma3_research_sweep.py`, not by `run_llm_strategy_sweep()` itself.

Recommendation:
Update the doc line so future agents do not assume the library runner creates plots/aggregate files directly.

## Tests Run

```text
python -m pytest tests/test_llm_sweep.py tests/test_plots.py
# 71 passed

python scripts\run_gemma3_research_sweep.py --help
# help command works

python -m pytest
# 314 passed, 2 skipped
```

## Summary

The core sweep implementation is sound: it creates fresh clients/envs per run, writes per-run logs, produces a combined CSV, and passes the full suite. The main fixes needed are around research-output fidelity and reproducibility: preserve the penalty dimension in plots, enrich the manifest, avoid silent plot failures, and correct the CLAUDE.md runner description.
