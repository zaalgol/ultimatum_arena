# Stage 3 Prompt: Add Expected-Value Research Preset

You are working on the Python project `ultimatum_arena`.

Goal:
Add a focused research preset that compares `deceptive`, `risk_aware`, and `expected_value`.

Important constraints:
- Do not remove existing `smoke`, `research`, or `risk` presets.
- Do not make `smoke` slow.
- Do not add paid providers.
- Do not add async/concurrency.
- Keep CLI behavior backward compatible.

Files to inspect:
- `scripts/run_gemma3_research_sweep.py`
- `tests/test_research_sweep_script.py`
- `ultimatum_arena/runners/llm_sweep.py`

Files to edit:
- `scripts/run_gemma3_research_sweep.py`
- `tests/test_research_sweep_script.py`

Preset design:
Add a new preset:

```text
ev
```

Recommended dimensions:
- strategies:
  - `honest_fair`
  - `deceptive`
  - `risk_aware`
  - `expected_value`
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
4 strategies * 4 audit probs * 3 penalties * 3 seeds = 144 runs
```

Expected CLI:

```bash
python scripts/run_gemma3_research_sweep.py --preset ev --model gemma3
```

Overrides must still work:

```bash
python scripts/run_gemma3_research_sweep.py --preset ev --rounds 10 --seeds 1
```

Expected output:
- same output layout as existing research sweep:
  - `runs/`
  - `combined_summary.csv`
  - `aggregate_by_strategy_audit_penalty.csv`
  - `manifest.json`
  - `plots/`
- manifest should record `preset = "ev"`.

Script output:
- Existing summary table should include `expected_value`.
- If a risk/EV audit-risk table exists, include `expected_value` when present or add a second table:

```text
Expected-value deception by audit probability
```

Keep output concise.

Tests:
- `ev` is an accepted preset.
- `ev` includes `expected_value`.
- `ev` includes `honest_fair`, `deceptive`, and `risk_aware`.
- `ev` dimensions match the design above.
- total runs for `ev` is 144.
- existing presets remain unchanged.
- argument overrides still parse correctly.

Commands to run:

```bash
python scripts/run_gemma3_research_sweep.py --help
python -m pytest tests/test_research_sweep_script.py
python -m pytest
```

Optional manual smoke, only if Ollama is available:

```powershell
python scripts\run_gemma3_research_sweep.py --preset ev --rounds 5 --seeds 1 --audit-probs 0.0 1.0 --lie-penalties 0 50 --model gemma3
```

Definition of done:
- `--preset ev` exists and is documented in CLI help.
- Existing presets still work.
- Full test suite passes.

