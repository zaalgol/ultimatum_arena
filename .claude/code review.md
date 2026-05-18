# Code Review

## Findings

### P2 - Probe script runs 9 cells while documentation/tests promise 3 paired cells

File: `scripts/probe_gemma3_expected_value.py`, lines 128-154

`_probe_cells()` defines three intended `(audit_prob, lie_penalty)` pairs, but `main()` splits those pairs into separate `audit_probs` and `lie_penalties` lists and passes them to `run_llm_strategy_sweep()`. That runner performs a Cartesian grid over all audit probabilities and all penalties, so the probe runs `3 × 3 × 1 = 9` cells instead of the promised 3 cells. This makes the "fast" probe about three times larger, produces extra conditions not listed in the stage prompt/docs, and makes the printed/documented interpretation misleading.

Suggested fix: either run the three cells explicitly one pair at a time, or add a small probe-specific loop that calls `run_llm_strategy_sweep()` with one audit probability and one penalty per cell and concatenates the rows. Add a regression test that monkeypatches `run_llm_strategy_sweep()` and asserts the script invokes exactly the three `_probe_cells()` pairs, not the Cartesian product.

### P2 - Hook settings were changed in an unrelated way

File: `.claude/settings.local.json`, lines 21-39

This change removes the previous async/rewake behavior from both hooks and adds very specific command permissions. That is unrelated to calibrating the expected-value strategy or adding the probe script, and it changes the developer workflow: the CLAUDE.md updater now blocks synchronously, and the review hook no longer has the explicit rewake behavior for surfacing review findings. Unless this was intentional, revert the hook-behavior edits and keep only changes that are necessary for this task.

### P3 - Probe script has mojibake in user-facing error messages

File: `scripts/probe_gemma3_expected_value.py`, lines 157, 162, 166

The arrow character is rendered as `â†’` in error messages. This does not break execution, but it looks broken in the terminal. Replace it with ASCII `->` or save the file consistently as UTF-8 and verify the terminal display.

## Tests Run

- `python -m pytest tests/test_llm_agents.py tests/test_research_sweep_script.py` -> 196 passed
- `python scripts\probe_gemma3_expected_value.py --help` -> help command works
- `python -m pytest` -> 422 passed, 2 skipped

## Summary

The calibrated prompt and test coverage are broadly moving in the right direction, and the suite is green. The main blocker before committing is the probe script's accidental Cartesian expansion: it is not actually the advertised 3-cell diagnostic probe. The hook settings change also looks unrelated and should be reverted unless there is a separate reason for it.
