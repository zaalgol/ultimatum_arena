# Stage 1 Prompt: Design Audit for Risk-Aware Proposer Strategy

You are working on the Python project `ultimatum_arena`.

Goal:
Plan the next Hidden Pie + Audit research step: add a fourth LLM proposer strategy called `risk_aware`.

This stage is design/audit only. Do not write implementation code in this stage.

Context:
The project already supports:
- `HiddenPieAuditEnv`
- `LLMProposer(client, strategy=...)`
- proposer strategies:
  - `honest_fair`
  - `self_interested`
  - `deceptive`
- `LLMResponder`
- `OllamaLLMClient`
- `FakeLLMClient`
- `run_llm_strategy_sweep()`
- `scripts/run_gemma3_research_sweep.py`
- research outputs under `outputs/gemma3_research/<timestamp>/`

Current research finding:
The `deceptive` strategy is intentionally instructed to lie, so it keeps lying even when audit probability and lie penalty are high. That is useful for payoff analysis, but it does not test whether Gemma can adaptively decide whether deception is worth the risk.

Next research question:
Does Gemma reduce deception when expected audit cost rises?

Proposed new strategy:

```text
risk_aware
```

Behavior:
- sees true pie, audit probability, and lie penalty
- can choose honest reporting or deceptive underclaiming
- should compare deception benefit against expected audit cost
- should lie more when audit probability/penalty is low
- should become more honest when audit probability/penalty is high
- must still output exactly the same JSON action schema:
  `{"claimed_pie": <number>, "offer": <number>, "public_message": "<string>"}`

Files to inspect:
- `ultimatum_arena/llm/prompts.py`
- `ultimatum_arena/llm/agents.py`
- `tests/test_llm_agents.py`
- `ultimatum_arena/runners/llm_sweep.py`
- `scripts/run_gemma3_research_sweep.py`
- `tests/test_llm_sweep.py`
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`

Your task:
1. Inspect the files above.
2. Confirm the smallest implementation path.
3. Do not edit files.
4. In your final response, provide:
   - exact files to edit in Stage 2
   - expected prompt wording principles for `risk_aware`
   - tests needed
   - whether sweep presets should include `risk_aware` by default or only in a new preset

Constraints:
- Do not add paid providers.
- Do not add OpenAI, Anthropic, Gemini API, or cloud clients.
- Do not add async/concurrency.
- Do not change environment rules.
- Do not change action/result schemas unless absolutely necessary.
- Keep current strategies working.

Definition of done:
- No code changed.
- There is a clear plan for implementing `risk_aware`.

