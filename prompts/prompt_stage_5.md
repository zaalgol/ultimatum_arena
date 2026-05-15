# Stage 5 Prompt: Documentation, Cleanup, And Final Verification

You are working on the Python project `ultimatum_arena`.

Goal:
Finalize the research-grade Hidden Pie + Audit experiment workflow documentation and run final verification.

Important constraints:
- Do not add new features in this stage unless they are tiny cleanup fixes required by tests or docs.
- Do not add paid provider clients.
- Do not add async/concurrency.
- Do not commit generated outputs.
- Keep docs concise but accurate.

Files to inspect:
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `.gitignore`
- `.claude/settings.local.json`
- `scripts/run_gemma3_research_sweep.py`
- `scripts/run_gemma3_strategy_set.ps1`
- `ultimatum_arena/runners/llm_sweep.py`
- `ultimatum_arena/analysis/plots.py`

Files to edit if needed:
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `.gitignore` only if new generated output paths are not ignored

Documentation should cover:
- Hidden Pie + Audit is complete as the first MVP.
- Heuristic demo:
  - `python scripts/run_hidden_pie_demo.py`
- Single Gemma demo:
  - `python scripts/run_gemma3_hidden_pie_demo.py`
- Sequential Gemma strategy demo:
  - `powershell -ExecutionPolicy Bypass -File scripts/run_gemma3_strategy_set.ps1`
- Research sweep:
  - `python scripts/run_gemma3_research_sweep.py --preset smoke`
  - `python scripts/run_gemma3_research_sweep.py --preset research`
- Output directories:
  - `outputs/hidden_pie_demo/`
  - `outputs/gemma3_demo/`
  - `outputs/gemma3_research/`
- Gemma/Ollama setup:
  - `ollama pull gemma3`
  - `Invoke-RestMethod http://localhost:11434/api/tags`
  - clarify that `ollama serve` reporting port `11434` is already in use means Ollama is already running
- Proposer strategies:
  - `honest_fair`
  - `self_interested`
  - `deceptive`
- Research interpretation:
  - deceptive strategy should usually underclaim and offer about half of the claimed pie
  - audit rate and lie detection should vary with audit probability
  - results should be interpreted across seeds, not single runs
- Current phase status:
  - Phase 1 complete
  - Phase 2 foundation complete
  - Phase 3A local Ollama/Gemma complete
  - Paid providers planned later
  - Phase 4 systematic comparisons now supported/starting
- Claude hooks:
  - CLAUDE maintenance hook
  - review-agent hook
  - generated outputs ignored

Verification commands:

```bash
python -m pytest
python scripts/run_gemma3_research_sweep.py --help
```

Optional manual smoke if Ollama is available:

```powershell
python scripts\run_gemma3_research_sweep.py --preset smoke --model gemma3
```

Definition of done:
- Docs accurately describe the current code.
- Full test suite passes.
- Help command works.
- `.gitignore` ignores generated research outputs through `outputs/`.
- No generated output files are added as source.

