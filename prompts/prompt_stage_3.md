# Stage 3 Prompt: Add Risk-Aware Research Preset

You are working on the Python project `ultimatum_arena`.

Goal:
Add a focused research preset that compares `risk_aware` against existing proposer strategies without making every default run too expensive.

Important constraints:
- Do not remove existing `smoke` or `research` presets.
- Do not make `smoke` slow.
- Do not add paid providers.
- Do not add async/concurrency.
- Keep CLI behavior backward compatible.

Files to inspect:
- `scripts/run_gemma3_research_sweep.py`
- `ultimatum_arena/runners/llm_sweep.py`
- `tests/test_llm_sweep.py`
- existing script tests if any

Files to edit:
- `scripts/run_gemma3_research_sweep.py`
- Add tests only if the project already has script-level CLI tests or if you can add small pure argument-parsing tests without invoking Ollama.

Preset design:
Add a new preset:

```text
risk
```

Recommended dimensions:
- strategies:
  - `honest_fair`
  - `deceptive`
  - `risk_aware`
- audit probabilities:
  - `[0.0, 0.25, 0.5, 1.0]`
- lie penalties:
  - `[0.0, 25.0, 50.0]`
- seeds:
  - `[1, 2, 3]`
- rounds:
  - `50`

Total runs:

```text
3 strategies * 4 audit probs * 3 penalties * 3 seeds = 108 runs
```

Expected CLI:

```bash
python scripts/run_gemma3_research_sweep.py --preset risk --model gemma3
```

Also ensure users can still override:

```bash
python scripts/run_gemma3_research_sweep.py --preset risk --rounds 10 --seeds 1
```

Expected output:
- same output layout as existing research sweep:
  - `runs/`
  - `combined_summary.csv`
  - `aggregate_by_strategy_audit_penalty.csv`
  - `manifest.json`
  - `plots/`
- manifest should record `preset = "risk"`.

Tests:
- If script argument parsing is testable without running Ollama, add tests that:
  - `risk` is an accepted preset
  - its dimensions match the design above
  - overrides still work
- If not adding tests, run help command and full existing tests.

Commands to run:

```bash
python scripts/run_gemma3_research_sweep.py --help
python -m pytest
```

Optional manual smoke, only if Ollama is available:

```powershell
python scripts\run_gemma3_research_sweep.py --preset risk --rounds 5 --seeds 1 --audit-probs 0.0 1.0 --lie-penalties 0 50 --model gemma3
```

Definition of done:
- `--preset risk` exists and is documented in CLI help.
- Existing `smoke` and `research` presets still work.
- Full test suite passes.

