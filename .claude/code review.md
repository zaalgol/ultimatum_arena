# Code Review

## Findings

### P2 - `summarize_adaptive_strategies()` silently hides malformed rows

File: `ultimatum_arena/analysis/sweep_summary.py`, lines 124-131

`summarize_adaptive_strategies()` catches every `ValueError` raised by `summarize_strategy_by_audit_risk()` and treats it as "strategy not present." That is broader than the documented behavior. The underlying helper also raises `ValueError` for malformed numeric fields, for example a CSV-loaded row with `audit_prob="bad"` or `lie_penalty="not-a-number"`. In that case the adaptive helper silently drops the strategy instead of surfacing a data-quality problem, which can make research summaries look valid while omitting corrupted rows.

Suggested fix: only skip strategies that truly have no matching rows. One clean approach is to pre-check whether any row has the requested strategy and optional lie penalty before calling `summarize_strategy_by_audit_risk()`, then let conversion/data errors propagate. Add a regression test where a matching `expected_value` row has an invalid numeric field and assert that `summarize_adaptive_strategies()` raises instead of returning `[]`.

### P3 - Wording says "all four adaptive strategies," but not all four are adaptive

Files: `scripts/run_gemma3_research_sweep.py`, `README.md`, `CLAUDE.md`, `AGENTS.md`

The `ev` preset compares `honest_fair`, `deceptive`, `risk_aware`, and `expected_value`, but the docs/help text call this "all four adaptive strategies." `honest_fair` is a baseline and `deceptive` is instruction-driven, so this phrasing is misleading. Prefer "all four comparison strategies" or "four proposer strategies."

## Tests Run

- `python scripts\run_gemma3_research_sweep.py --help`
- Valid CSV-string smoke check for `summarize_strategy_by_audit_risk()` and `summarize_adaptive_strategies()`
- `python -m pytest` -> 397 passed, 2 skipped

## Summary

The `expected_value` strategy, `ev` preset, exports, docs, and tests are mostly in good shape. The main issue to fix before committing is the broad `ValueError` catch in `summarize_adaptive_strategies()`, because it can hide malformed experiment data.
