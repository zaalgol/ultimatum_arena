# Stage 5 Prompt: Documentation and Final Verification for Risk-Aware Strategy

You are working on the Python project `ultimatum_arena`.

Goal:
Update documentation and final checks after adding `risk_aware`.

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
- `ultimatum_arena/analysis/plots.py` or any new analysis helper module

Files to edit if needed:
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`

Documentation updates:
1. Add `risk_aware` to proposer strategy descriptions:
   - chooses whether to report honestly or underclaim based on audit probability and penalty
   - intended to test adaptive deception
2. Document the new preset:

```bash
python scripts/run_gemma3_research_sweep.py --preset risk --model gemma3
```

3. Explain the research interpretation:
   - `deceptive` is instruction-driven deception
   - `risk_aware` is incentive-sensitive deception
   - compare whether `risk_aware` deception falls as audit probability or penalty rises
4. Keep phase boundaries clear:
   - still local Ollama/Gemma only
   - no paid provider clients yet
   - no new game variants yet
5. Mention any new analysis helper/table if Stage 4 added one.

Verification commands:

```bash
python -m pytest
python scripts/run_gemma3_research_sweep.py --help
```

Optional manual run if Ollama is available:

```powershell
python scripts\run_gemma3_research_sweep.py --preset risk --rounds 5 --seeds 1 --audit-probs 0.0 1.0 --lie-penalties 0 50 --model gemma3
```

Definition of done:
- Docs accurately describe `risk_aware`.
- Docs accurately describe the new preset and current local-only provider state.
- Full test suite passes.
- Help command works.

