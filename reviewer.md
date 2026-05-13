# Review: LLM Observability and Gemma Prompt Update

## Commands Run

- `python -m pytest tests/test_llm_agents.py tests/test_runner.py`
  - Result: `89 passed`
- `python -m pytest`
  - Result: `228 passed, 2 skipped`
- Attempted: `python -m pytest tests/test_llm_agents.py tests/test_runner.py tests/test_storage.py`
  - Result: failed because `tests/test_storage.py` does not exist in this repository.
- Manual prompt check with `HiddenPieAuditEnv(audit_prob=0.25, lie_penalty=25.0)`.

## Findings

### P1: Configured audit probability and lie penalty are not passed into LLM prompts

Files:
- `ultimatum_arena/llm/prompts.py:66`
- `ultimatum_arena/schemas/observations.py:6`
- `ultimatum_arena/schemas/observations.py:16`
- `ultimatum_arena/runners/basic.py:59`

The new proposer prompt displays audit probability and lie penalty, but `build_proposer_prompt()` reads them from `ProposerObservation` using `getattr(..., 0.0)`. `ProposerObservation` does not contain `audit_prob` or `lie_penalty`, so every normal run tells the proposer:

```text
Audit probability: 0%
Lie penalty (if caught): 0.00
```

This happens even when the environment is configured with `audit_prob=0.25` and `lie_penalty=25.0`. I verified this manually through `run_experiment()` metadata.

This is important because the goal of the prompt update was to make Gemma reason about audit incentives. Right now, the prompt actively gives the wrong incentive information. The responder prompt also does not receive audit/penalty details, despite the intended design saying the responder should judge the offer using audit setting if available.

Recommendation:
Add public audit settings to the observation schema, or otherwise pass them through a clean runner/env path before prompt construction. Since these are game-level public parameters, the cleanest fix is likely to add optional or required `audit_prob` and `lie_penalty` fields to `ProposerObservation` and `ResponderObservation`, populate them in `HiddenPieAuditEnv.proposer_observation()` and `HiddenPieAuditEnv.responder_observation()`, and update tests to assert the actual configured values appear in prompts.

### P2: Tests check prompt keywords, but not configured prompt values

File:
- `tests/test_llm_agents.py`

The new tests assert that prompts mention audit/penalty concepts, but they do not verify that the configured values from the environment are present. This allowed the `0% / 0.00` issue above to pass.

Recommendation:
Add a runner/env-level test that creates `HiddenPieAuditEnv(audit_prob=0.25, lie_penalty=25.0)`, runs one LLM round, and asserts the stored proposer/responder prompt metadata contains `25%` / `25.0` or equivalent.

## Non-Blocking Notes

1. `RoundResult.metadata` is a reasonable backward-compatible extension. Existing JSONL logs without metadata should continue loading because the field has a default factory.

2. `run_experiment()` captures `last_prompt`, `last_raw_response`, and parse errors for agents that expose those attributes. This is a small, useful extension and does not force heuristic agents to participate.

3. The LLM agent docstrings say parse error is set "if parsing failed and a fallback was used," but the implementation raises on parse failure rather than falling back. This is just wording drift; either change the docstring later or add retry/fallback behavior in a separate task if desired.

4. Prompt source uses Unicode punctuation such as en dashes and arrows. The file is valid UTF-8, but PowerShell displays some characters as mojibake in this environment. For future terminal-facing text, ASCII is still safer on Windows.

## What Looks Good

- Raw LLM observability is now available on `LLMProposer` and `LLMResponder`.
- `run_experiment()` persists LLM metadata into `RoundResult` and JSONL output.
- Heuristic runs keep empty metadata and are not forced into the LLM path.
- Full test suite passes: `228 passed, 2 skipped`.
- The change stays within the existing synchronous `BaseProposer` / `BaseResponder` architecture.
- No paid API provider code was added.

## Recommendation

Do not treat this task as fully complete yet. The observability part is good, but the prompt improvement has a material correctness bug because configured audit probability and lie penalty are not reaching the LLM prompts. Fix that before running more Gemma experiments.
