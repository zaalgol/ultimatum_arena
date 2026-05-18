# Stage 1 Prompt: Design Audit for Expected-Value Strategy

You are working on the Python project `ultimatum_arena`.

Goal:
Plan the next Hidden Pie + Audit research step: add a fifth LLM proposer strategy called `expected_value`.

This stage is design/audit only. Do not write implementation code in this stage.

Context:
The project already supports:
- `HiddenPieAuditEnv`
- `LLMProposer(client, strategy=...)`
- proposer strategies:
  - `honest_fair`
  - `self_interested`
  - `deceptive`
  - `risk_aware`
- `LLMResponder`
- `OllamaLLMClient`
- `FakeLLMClient`
- `run_llm_strategy_sweep()`
- `scripts/run_gemma3_research_sweep.py`
- presets:
  - `smoke`
  - `research`
  - `risk`
- `summarize_strategy_by_audit_risk()`

Current research finding:
The `risk_aware` strategy did not lie at all, even when audit probability and penalty were zero. It behaved like a cautious/ethical generous baseline, not like a payoff-maximizing expected-value strategist.

Next research question:
Can Gemma choose deception based on explicit expected-value/payoff-maximization logic?

Proposed new strategy:

```text
expected_value
```

Intended behavior:
- compare expected payoff from honest reporting versus underclaiming
- account for audit probability and lie penalty
- use approximate arithmetic, but do not expose chain-of-thought
- underclaim when expected payoff is higher
- report honestly when expected audit cost makes deception unattractive
- produce the same JSON schema:
  `{"claimed_pie": <number>, "offer": <number>, "public_message": "<string>"}`

Important distinction:
- `risk_aware` = cautious and incentive-aware, may avoid lying.
- `expected_value` = explicitly self-interested expected-payoff maximizer.
- `deceptive` = instruction-driven deception regardless of risk.

Files to inspect:
- `ultimatum_arena/llm/prompts.py`
- `ultimatum_arena/llm/agents.py`
- `tests/test_llm_agents.py`
- `scripts/run_gemma3_research_sweep.py`
- `tests/test_research_sweep_script.py`
- `ultimatum_arena/analysis/sweep_summary.py`
- `tests/test_sweep_summary.py`
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`

Your task:
1. Inspect the files above.
2. Confirm the smallest implementation path.
3. Do not edit files.
4. In your final response, provide:
   - exact files to edit in Stage 2
   - expected prompt wording principles for `expected_value`
   - tests needed
   - whether to add a new preset or extend `risk`
   - risks/open questions

Constraints:
- Do not add paid providers.
- Do not add OpenAI, Anthropic, Gemini API, or cloud clients.
- Do not add async/concurrency.
- Do not change environment rules.
- Do not change action/result schemas unless absolutely necessary.
- Keep current strategies working.

Definition of done:
- No code changed.
- There is a clear plan for implementing `expected_value`.

