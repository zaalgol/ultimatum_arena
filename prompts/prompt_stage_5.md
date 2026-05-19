# Stage 5: Documentation And Full Sweep Recommendation

You are Claude Code working in the `ultimatum_arena` repository.

## Goal

Update documentation to describe the expected-value baseline/probe workflow and give a clear recommendation for the next full sweep.

## Files To Inspect

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `scripts/probe_expected_value_comparison.py`
- `scripts/probe_gemma3_expected_value.py`
- `ultimatum_arena/agents/heuristics.py`
- `ultimatum_arena/llm/prompts.py`

## Files To Edit

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`

## Documentation Should Include

- `ExpectedValueProposer` is deterministic and non-LLM.
- It is a benchmark for whether the game incentives create expected behavior.
- `expected_value` is a Gemma prompt strategy that may still fail to adapt.
- `payoff_table` is a structured Gemma prompt strategy intended to follow candidate payoff comparisons.
- `probe_expected_value_comparison.py` is the fast diagnostic before full sweeps.
- Where outputs are saved.

## Commands To Run

```powershell
python -m pytest
```

Do not run long live Gemma sweeps in this documentation stage unless explicitly asked.

## Constraints

- Keep docs concise.
- Do not claim Gemma is rational unless probe results support it.
- Do not add paid providers.
- Do not add Phase 5 game variants.

## Definition Of Done

- Docs describe the calculator baseline and payoff-table probe workflow.
- Full test suite passes.
- Provide exact recommended next command, depending on Stage 4 results.
