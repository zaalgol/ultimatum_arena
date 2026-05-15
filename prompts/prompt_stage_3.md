# Stage 3 Prompt: Add Gemma Research Sweep CLI Script

You are working on the Python project `ultimatum_arena`.

Goal:
Add a command-line script that runs the reusable LLM strategy sweep with local Gemma through Ollama.

Important constraints:
- Use only local Ollama/Gemma.
- No OpenAI, Anthropic, Gemini API, or paid provider clients.
- No async/concurrency.
- Do not rewrite the sweep runner from Stage 2.
- Keep the script simple and explicit.
- The script should fail clearly if Ollama is unavailable.

Files to inspect:
- `ultimatum_arena/runners/llm_sweep.py`
- `scripts/run_gemma3_hidden_pie_demo.py`
- `scripts/run_gemma3_strategy_set.ps1`
- `ultimatum_arena/llm/ollama_client.py`
- `ultimatum_arena/llm/errors.py`
- `README.md`
- `CLAUDE.md`

Files to create or edit:
- Create `scripts/run_gemma3_research_sweep.py`
- Add tests only if the project already has a script-test pattern; otherwise keep script logic small and rely on runner tests

CLI behavior:
The script should write outputs under:

```text
outputs/gemma3_research/YYYYMMDD_HHMMSS/
```

Support presets:

```bash
python scripts/run_gemma3_research_sweep.py --preset smoke
python scripts/run_gemma3_research_sweep.py --preset research
```

Preset `smoke`:
- strategies: `honest_fair`, `deceptive`
- audit probabilities: `[0.0, 0.25, 1.0]`
- lie penalties: `[0.0, 25.0]`
- seeds: `[1]`
- rounds: `10`

Preset `research`:
- strategies: `honest_fair`, `self_interested`, `deceptive`
- audit probabilities: `[0.0, 0.1, 0.25, 0.5, 0.75, 1.0]`
- lie penalties: `[0.0, 10.0, 25.0, 50.0]`
- seeds: `[1, 2, 3]`
- rounds: `50`

Also support overrides:
- `--model gemma3`
- `--temperature 0.2`
- `--rounds 20`
- `--strategies honest_fair deceptive`
- `--audit-probs 0.0 0.25 1.0`
- `--lie-penalties 0 25 50`
- `--seeds 1 2 3`
- `--output-root outputs/gemma3_research`

Expected terminal behavior:
- print run ID and output directory
- print selected preset and dimensions
- print total number of runs before starting
- print a concise final table with one row per configuration or at least a summary grouped by strategy
- print path to `combined_summary.csv`
- if Ollama is unavailable or model missing, print a clear error and exit nonzero

Implementation notes:
- Use `OllamaLLMClient(model=args.model, temperature=args.temperature)`.
- Use fresh clients per run through factories:
  - `proposer_client_factory=lambda: OllamaLLMClient(...)`
  - `responder_client_factory=lambda: OllamaLLMClient(...)`
- Use `run_llm_strategy_sweep(...)`.
- Output root should be timestamped.
- Do not run this script from tests against real Ollama.

Manual smoke command after implementation:

```powershell
python scripts\run_gemma3_research_sweep.py --preset smoke --model gemma3
```

Commands to run:

```bash
python -m pytest tests/test_llm_sweep.py
python -m pytest
python scripts/run_gemma3_research_sweep.py --help
```

Definition of done:
- The script parses arguments and shows useful help.
- The script can run the smoke preset when Ollama is available.
- Outputs are written under `outputs/gemma3_research/<timestamp>/`.
- No paid providers or API keys are introduced.

