# Stage 5: Update Documentation And Prepare Full EV Sweep

You are Claude Code working in the `ultimatum_arena` repository.

## Goal

If the expected-value probe from Stage 4 shows useful behavior, update documentation so the current research workflow is clear. Then provide the exact command for the user to run the full `ev` sweep.

## Files To Edit

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`

Only edit prompt files if they need small corrections:

- `prompts/prompt_stage_1.md`
- `prompts/prompt_stage_2.md`
- `prompts/prompt_stage_3.md`
- `prompts/prompt_stage_4.md`
- `prompts/prompt_stage_5.md`

## Documentation Should Include

- `expected_value` is a calibrated numeric expected-payoff proposer strategy.
- `risk_aware` is a cautious incentive-aware strategy that may avoid lying.
- `deceptive` is an instruction-driven lying baseline.
- `probe_gemma3_expected_value.py` is the fast calibration check.
- `run_gemma3_research_sweep.py --preset ev --model gemma3` is the full comparison.
- Outputs are timestamped under:
  - `outputs/gemma3_expected_value_probe/`
  - `outputs/gemma3_research/`

## Commands To Run

```powershell
python -m pytest
```

Do not run the full live Gemma sweep in this documentation stage unless the user explicitly asks.

## Constraints

- Keep documentation concise and accurate.
- Do not claim paid provider support exists.
- Do not claim the strategy proves rationality; describe it as prompt-calibrated behavior for research.
- Do not add Phase 5 game variants.

## Definition Of Done

- Docs describe the calibrated expected-value workflow.
- Full test suite passes.
- Provide the user with the exact full-sweep command:

```powershell
python scripts/run_gemma3_research_sweep.py --preset ev --model gemma3
```
