# Code Review

> **Status: HISTORICAL — resolved, retained for reference (as of 2026-06-23).**
> This is a snapshot of a past review, not an active to-do list. Do not reopen these findings without re-verifying against current code.
>
> - **P2 `ExpectedValueProposer` validation** — RESOLVED. `__init__()` now validates all fractions (`ultimatum_arena/agents/proposers.py:107-114`).
> - **P2 hook-settings churn** — historical note about `.claude/settings.local.json`; verify against current settings before acting.
> - **P3 transient probe outcomes** — partially addressed; `README.md`/`CLAUDE.md` now phrase Gemma observations as model-/temperature-/seed-dependent. `AGENTS.md` referenced below no longer exists (merged into `CLAUDE.md`).

## Findings

### P2 - `ExpectedValueProposer` accepts invalid fraction parameters and fails later in `act()`

File: `ultimatum_arena/agents/proposers.py`, lines 100-110

`ExpectedValueProposer` exposes configurable fractions, but `__init__()` does not validate them. Values such as `offer_fraction_of_claim=1.5`, `moderate_claim_fraction=-0.2`, or `honest_offer_fraction=1.2` can create invalid `ProposerAction`s later (`offer > claimed_pie`, negative/zero `claimed_pie`, etc.). Existing heuristic agents validate comparable public knobs (`LyingGreedyProposer.claimed_fraction`), and this new class is meant to be a stable research baseline, so it should fail early with clear `ValueError`s.

Suggested fix: validate all fractions in `__init__()`. At minimum require `0 <= honest_offer_fraction <= 1`, `0 < moderate_claim_fraction <= 1`, `0 < aggressive_claim_fraction <= 1`, and `0 <= offer_fraction_of_claim <= 1`. Add tests for invalid values.

### P2 - Hook settings were changed in an unrelated way

File: `.claude/settings.local.json`, lines 7-40

This change again alters the local Claude workflow while the requested feature work was expected-value baselines/probes. It adds broad curl/ollama/temp read permissions and removes the previous async/rewake hook behavior. That is unrelated to the application code and changes how future tool hooks behave. Unless this was explicitly intentional, revert the `.claude/settings.local.json` changes in this feature branch.

### P3 - Docs state transient Gemma probe outcomes as if they are stable project facts

Files: `README.md`, `CLAUDE.md`, `AGENTS.md`

The docs say things like Gemma 3 `payoff_table` reports honestly in all observed rounds and `expected_value` reliably underclaims. Those may be true for one local run, but they depend on model version, Ollama behavior, temperature, prompt changes, and seed. Prefer wording like "in the latest local probe" with the exact output path/date if you want to document an observation, or describe intended interpretation without freezing one run as a permanent fact.

## Tests Run

- `python -m pytest tests/test_agents.py tests/test_llm_agents.py tests/test_research_sweep_script.py tests/test_ollama_client.py` -> 282 passed, 2 skipped
- `python scripts\probe_expected_value_comparison.py --help` -> help command works
- `python -m pytest` -> 473 passed, 2 skipped

## Summary

The main application changes are structurally sound: the deterministic baseline, `payoff_table` prompt, and comparison probe are in place and covered by tests. I would fix parameter validation and revert the unrelated hook-settings churn before committing.
