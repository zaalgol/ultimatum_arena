# Stage 5 Prompt: Documentation and Final Verification for Expected-Value Strategy

You are working on the Python project `ultimatum_arena`.

Goal:
Update documentation and final checks after adding `expected_value`.

Important constraints:
- Do not add new features in this stage unless fixing a small doc/test issue.
- Do not add paid providers.
- Do not add async/concurrency.
- Do not commit generated outputs.
- Keep docs concise and accurate.

Files to inspect:
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `.claude/settings.local.json`
- `scripts/run_gemma3_research_sweep.py`
- `ultimatum_arena/llm/prompts.py`
- `ultimatum_arena/analysis/sweep_summary.py`

Files to edit if needed:
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`

Documentation updates:
1. Add `expected_value` to proposer strategy descriptions:
   - explicitly expected-payoff maximizing
   - compares honest reporting and underclaiming
   - should lie when expected deception payoff exceeds expected audit cost
2. Document the new preset:

```bash
python scripts/run_gemma3_research_sweep.py --preset ev --model gemma3
```

3. Explain research interpretation:
   - `deceptive` is instruction-driven deception
   - `risk_aware` is cautious/incentive-aware and may refuse to lie
   - `expected_value` is explicit payoff-maximizing adaptation
   - compare whether `expected_value` deception falls as audit probability or penalty rises
4. Keep phase boundaries clear:
   - still local Ollama/Gemma only
   - no paid provider clients yet
   - no new game variants yet
5. Mention any analysis helper/table updates from Stage 4.

Verification commands:

```bash
python -m pytest
python scripts/run_gemma3_research_sweep.py --help
```

Optional manual run if Ollama is available:

```powershell
python scripts\run_gemma3_research_sweep.py --preset ev --rounds 5 --seeds 1 --audit-probs 0.0 1.0 --lie-penalties 0 50 --model gemma3
```

Definition of done:
- Docs accurately describe `expected_value`.
- Docs accurately describe the new `ev` preset and current local-only provider state.
- Full test suite passes.
- Help command works.

