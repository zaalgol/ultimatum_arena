# Stage 1: Add Deterministic Expected-Value Proposer Baseline

You are Claude Code working in the `ultimatum_arena` repository.

## Goal

Add a non-LLM deterministic proposer baseline that implements expected-value action selection directly. This gives the research project a controlled benchmark for whether the game incentives behave as expected.

This is not a replacement for LLM agents. It is a calculator/heuristic baseline used to compare against Gemma strategies.

## Files To Inspect

- `ultimatum_arena/agents/base.py`
- `ultimatum_arena/agents/heuristics.py`
- `ultimatum_arena/agents/__init__.py`
- `ultimatum_arena/schemas/actions.py`
- `ultimatum_arena/schemas/observations.py`
- `tests/test_agents.py`

## Files To Edit

- `ultimatum_arena/agents/heuristics.py`
- `ultimatum_arena/agents/__init__.py`
- `tests/test_agents.py`

## Expected Behavior

Add a proposer class, suggested name:

```python
ExpectedValueProposer
```

It should subclass `BaseProposer` and implement:

```python
act(obs: ProposerObservation) -> ProposerAction
```

It should evaluate a small fixed candidate set and choose the action with the highest expected proposer payoff.

Suggested candidates:

- honest:
  - `claimed_pie = true_pie`
  - `offer = honest_offer_fraction * true_pie`
- moderate underclaim:
  - `claimed_pie = moderate_claim_fraction * true_pie`
  - `offer = offer_fraction_of_claim * claimed_pie`
- aggressive underclaim:
  - `claimed_pie = aggressive_claim_fraction * true_pie`
  - `offer = offer_fraction_of_claim * claimed_pie`

Suggested defaults:

```python
honest_offer_fraction = 0.45
moderate_claim_fraction = 0.65
aggressive_claim_fraction = 0.55
offer_fraction_of_claim = 0.5
```

Expected proposer payoff formula:

```text
true_pie - offer - audit_prob * lie_penalty
```

Only subtract audit cost for deceptive candidates where `claimed_pie != true_pie`.

Tie-breaking should be deterministic. Prefer less deception when expected payoffs are equal or extremely close.

The public message can be simple and consistent, e.g.:

```text
I claim a pie of X and offer Y.
```

## Edge Cases

- Ensure `offer <= claimed_pie`.
- Avoid negative values.
- Use the observation's `audit_prob` and `lie_penalty`.
- Keep values as floats; rounding is okay if consistent with existing agents.

## Tests To Add Or Update

In `tests/test_agents.py`, add tests that:

- `ExpectedValueProposer` is importable from `ultimatum_arena.agents`.
- At `audit_prob=0`, `lie_penalty=0`, it chooses a deceptive candidate.
- At `audit_prob=1`, high `lie_penalty`, it chooses honest reporting.
- It returns a valid `ProposerAction`.
- Tie-breaking prefers honest/less deceptive when payoffs are equal.

## Commands To Run

```powershell
python -m pytest tests/test_agents.py
python -m pytest
```

## Constraints

- Do not change environment logic.
- Do not change runner interfaces.
- Do not add LLM provider code.
- Do not add Phase 5 game variants.
- Keep this class small and explicit.

## Definition Of Done

- Deterministic expected-value proposer exists.
- It adapts to audit/penalty incentives in unit tests.
- It is exported from `ultimatum_arena.agents`.
- Full test suite passes.
