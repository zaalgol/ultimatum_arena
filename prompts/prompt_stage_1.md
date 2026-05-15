# Stage 1 Prompt: Audit Research-Grade Sweep Design

You are working on the Python project `ultimatum_arena`.

Goal:
Prepare the implementation of research-grade Hidden Pie + Audit experiments for local Gemma/Ollama agents. This stage is an audit/design stage only.

Do not write implementation code in this stage.

Context:
The project already has:
- `HiddenPieAuditEnv`
- heuristic agents and LLM agents
- `LLMProposer(strategy=...)` with strategies:
  - `honest_fair`
  - `self_interested`
  - `deceptive`
- `LLMResponder`
- `OllamaLLMClient`
- `FakeLLMClient`
- `run_experiment()`
- heuristic sweep support in `ultimatum_arena/runners/sweep.py`
- metrics, plots, JSONL, summary JSON, and demo scripts
- local Gemma demo scripts:
  - `scripts/run_gemma3_hidden_pie_demo.py`
  - `scripts/run_gemma3_strategy_set.ps1`

Research goal:
Move from manual demo runs to repeatable experiment suites that compare proposer strategies across audit probabilities, penalties, and seeds.

Files to inspect:
- `ultimatum_arena/runners/basic.py`
- `ultimatum_arena/runners/sweep.py`
- `ultimatum_arena/analysis/metrics.py`
- `ultimatum_arena/analysis/plots.py`
- `ultimatum_arena/llm/agents.py`
- `ultimatum_arena/llm/client.py`
- `ultimatum_arena/llm/ollama_client.py`
- `scripts/run_gemma3_hidden_pie_demo.py`
- `scripts/run_gemma3_strategy_set.ps1`
- `tests/test_sweep.py`
- `tests/test_llm_agents.py`
- `README.md`
- `CLAUDE.md`

Expected design:
We want a reusable LLM strategy sweep, probably in:

```text
ultimatum_arena/runners/llm_sweep.py
```

The sweep should run combinations of:
- proposer strategies: `honest_fair`, `self_interested`, `deceptive`
- audit probabilities
- lie penalties
- seeds
- rounds

The sweep should use:
- fresh `HiddenPieAuditEnv` per configuration
- fresh proposer and responder clients per run
- `LLMProposer(client=..., strategy=...)`
- `LLMResponder(client=...)`
- existing `run_experiment()`
- existing metrics

Desired outputs when `output_dir` is provided:

```text
outputs/gemma3_research/YYYYMMDD_HHMMSS/
  runs/
    <run_name>.jsonl
    <run_name>_summary.json
  combined_summary.csv
  manifest.json
  plots/    # added in a later stage
```

Design requirements:
- Use standard library `csv` and `json`.
- No pandas.
- No async/concurrency yet.
- No paid API providers.
- No OpenAI/Anthropic/Gemini API clients.
- No database or experiment tracking framework.
- Tests must use `FakeLLMClient`, not real Ollama.
- Preserve existing public interfaces unless there is a strong reason.
- Keep Phase 1 heuristic sweep behavior unchanged.

Your task:
1. Inspect the files listed above.
2. Identify the smallest implementation path.
3. Write a concise design note to the terminal or your final response. Do not edit code.
4. Include:
   - recommended function signature for `run_llm_strategy_sweep`
   - recommended row fields for `combined_summary.csv`
   - output directory layout
   - test plan
   - risks or open questions

Definition of done:
- No code files changed.
- You have a clear implementation plan for the next stage.
- You explicitly confirm the plan does not require real API keys or paid providers.

