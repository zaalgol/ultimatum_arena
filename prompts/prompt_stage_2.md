# Stage 2 Prompt: Add Reusable LLM Strategy Sweep Runner

You are working on the Python project `ultimatum_arena`.

Goal:
Implement the reusable sweep engine for research-grade Hidden Pie + Audit experiments with LLM agents, using fake clients in tests.

Important constraints:
- Do not add paid provider clients.
- Do not add OpenAI, Anthropic, Gemini API, or other remote provider code.
- Do not add async/concurrency.
- Do not rewrite `run_experiment()`.
- Do not break heuristic sweep behavior.
- Tests must not require Ollama or network access.
- Keep the implementation small and close to existing `runners/sweep.py` patterns.

Files to inspect:
- `ultimatum_arena/runners/sweep.py`
- `ultimatum_arena/runners/basic.py`
- `ultimatum_arena/llm/agents.py`
- `ultimatum_arena/llm/client.py`
- `ultimatum_arena/llm/prompts.py`
- `ultimatum_arena/envs/hidden_pie_audit.py`
- `ultimatum_arena/storage/jsonl.py`
- `tests/test_sweep.py`
- `tests/test_llm_agents.py`

Files to create or edit:
- Create `ultimatum_arena/runners/llm_sweep.py`
- Edit `ultimatum_arena/runners/__init__.py` if needed to export stable public functions
- Create `tests/test_llm_sweep.py`

Implementation target:
Add a function similar to:

```python
def run_llm_strategy_sweep(
    *,
    proposer_client_factory,
    responder_client_factory,
    strategies: list[str],
    audit_probabilities: list[float],
    lie_penalties: list[float],
    seeds: list[int],
    n_rounds: int,
    pie_range: tuple[float, float] = (50.0, 150.0),
    output_dir: str | Path | None = None,
    experiment_prefix: str = "gemma_strategy_sweep",
) -> list[dict]:
    ...
```

Design notes:
- `proposer_client_factory` and `responder_client_factory` must be called fresh for each run.
- For each configuration:
  - create a fresh `HiddenPieAuditEnv`
  - create a fresh proposer client
  - create a fresh responder client
  - create `LLMProposer(client=..., strategy=strategy)`
  - create `LLMResponder(client=...)`
  - call `run_experiment(...)`
- Each returned row should include all summary metrics plus configuration fields:
  - `strategy`
  - `audit_prob`
  - `lie_penalty`
  - `seed`
  - `n_rounds`
  - `model` if available from the client, otherwise omit or use `None`
  - `temperature` if available from the client, otherwise omit or use `None`
  - `proposer_class`
  - `responder_class`
- Use safe run names that can be used as filenames, for example:
  - `gemma_strategy_sweep_strategy-deceptive_audit-0p25_penalty-25_seed-42`
- If `output_dir` is provided:
  - create `output_dir / "runs"`
  - write per-run JSONL and summary JSON through existing `run_experiment()`
  - write `combined_summary.csv` at the root output directory
  - write `manifest.json` with sweep configuration
- Use standard library `csv` and `json`.
- CSV columns should be stable and deterministic. Include config columns first, then metric columns.

Tests to add:
- sweep returns the expected number of rows
- each row includes required config fields and metrics
- output directory contains:
  - `runs/`
  - per-run JSONL files
  - per-run summary JSON files
  - `combined_summary.csv`
  - `manifest.json`
- client factories are called once per run, proving fresh clients are used
- strategy is passed into `LLMProposer`
- invalid strategy should raise `ValueError` through `LLMProposer`
- tests use `FakeLLMClient`; no real Ollama

Suggested fake responses:
- proposer fake response:
  `{"claimed_pie": 100.0, "offer": 50.0, "public_message": "test"}`
- responder fake response:
  `{"accept": true}`

Commands to run:

```bash
python -m pytest tests/test_llm_sweep.py
python -m pytest tests/test_sweep.py
python -m pytest tests/test_llm_agents.py
python -m pytest
```

Definition of done:
- `run_llm_strategy_sweep()` works with `FakeLLMClient`.
- Per-run logs and summary files are written when `output_dir` is provided.
- Combined CSV and manifest JSON are written.
- Full test suite passes.
- No real provider or API key code is added.

