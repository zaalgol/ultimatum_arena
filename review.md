# Review: Hidden Pie Audit Research Plan

## Findings

### P1 - Claude refusals are treated as data in the plan, but the current execution path will likely abort on them

File: `research/hidden_pie_audit_research_plan.md`, lines 36-38, 121-127, 163-169

The plan correctly says Claude refusals should be counted as an alignment result, not as failed runs. But the current LLM flow treats non-JSON model output as `LLMParseError`; existing scripts generally catch that at the top level and exit. If Claude refuses in the first `deceptive` or `expected_value` canary, the run may stop before producing a refusal map or comparable per-cell rows.

Before spending Claude windows, the prerequisite probe should explicitly catch per-round proposer parse/refusal errors, persist the raw response, mark the row as `refusal` or `parse_error`, and continue to the next strategy/cell. Otherwise the headline "Claude refuses to deceive" finding may be lost as a script failure.

### P1 - The Section 0 prerequisite is larger than the plan makes it sound

File: `research/hidden_pie_audit_research_plan.md`, lines 114-127

Adding `--provider claude` is not enough. The probe also needs strategy selection, canonical-cell selection, proposer-only Claude calls with a heuristic responder, refusal-safe persistence, manifest fields that label "Claude Code CLI", and tests that prove no live Claude calls are needed in CI.

Recommendation: make Section 0's acceptance criteria explicit before running research:

- provider choices work for `ollama` and `claude`
- `--responder threshold` truly uses no model calls for the responder
- refusals produce rows instead of aborting
- output CSV/JSON includes `provider`, `model`, `strategy`, `audit_prob`, `lie_penalty`, `rounds`, `refusal_count`, and raw refusal examples

### P2 - "All six strategies" are not measured on the same grid

File: `research/hidden_pie_audit_research_plan.md`, lines 75-92, 137-151

The plan says all six LLM deception/EV strategies are covered, but the actual Gemma plan runs `expected_value` in the `ev` preset, `risk_aware` in `risk`/`ev`, and `payoff_table` only through the 3-cell comparison probe. `self_interested` is not included in Section 2's commands unless the `research` preset or a custom override is added.

That is fine if intentional, but the findings should not claim a uniform all-strategies grid. Either run a custom Gemma sweep with all six strategies on the same audit/penalty/seeds grid, or label the evidence levels separately: full grid vs canonical 3-cell probe.

### P2 - Detection sanity needs a minimum lie count

File: `research/hidden_pie_audit_research_plan.md`, lines 28-30, 53-55, 181-187

`lie_detection_rate_among_lies ~= audit_prob` is only meaningful when there are enough deceptive rounds. Honest/refusal cells will have zero or very few lies, making the metric either 0 or very noisy.

Add a rule such as: only interpret detection sanity when `n_lies >= 10` or report it as "insufficient lies." Otherwise high-honesty strategies may look like audit-mechanism failures when they simply did not lie.

### P2 - Audit-cost interpretation should be normalized

File: `research/hidden_pie_audit_research_plan.md`, lines 18-25, 83-84

The research question uses `audit_prob * lie_penalty`, but the incentive depends on that cost relative to true pie and the surplus from underclaiming. A penalty of 25 has different meaning when `true_pie` is near 50 vs 150.

Keep the current grid, but in the findings also report normalized audit cost, for example `audit_prob * lie_penalty / mean_true_pie`, or compare expected penalty against `mean_lie_size` / underclaim surplus. This will make intermediate cells easier to interpret.

### P2 - Responder sensitivity is underspecified

File: `research/hidden_pie_audit_research_plan.md`, lines 170-179

Section 5 is a good question, but it is not executable yet. It says "via run_experiment / a short script" without specifying grid, seeds, proposer parameters, output path, or exact metrics.

Before running, define the exact command or add a small script. Use the same audit grid and seeds as the heuristic baseline, and compare `ThresholdResponder` vs `SuspiciousResponder` on acceptance, proposer payoff, and responder share.

### P3 - Claude thresholds are coarse with 10 rounds

File: `research/hidden_pie_audit_research_plan.md`, lines 32-45, 160-169

The honesty/deception thresholds are useful, but with 10 rounds a threshold like `deception_rate <= 0.1` means only 0 or 1 deceptive action. A single parse failure or borderline claim changes the label.

In the write-up, report raw counts beside every rate, e.g. `1/10`, and avoid strong claims from one small Claude cell. The thresholds are fine as labels, not statistical proof.

## Strengths

- The plan asks the right central question: whether agents adapt deception to audit incentives.
- The deterministic `ExpectedValueProposer` is the right oracle.
- The plan correctly separates Prompt-Attack from Hidden Pie Audit.
- The Claude CLI labeling rule is careful and should prevent overclaiming.
- Proposer-only Claude sweeps are a good budget optimization for `deception_rate`.
- The refusal canary is the right first move, as long as refusals are captured structurally.

## Bottom Line

Do not execute the Claude sections until the prerequisite probe is refusal-safe. After that, the plan is strong. The main adjustments are to make strategy coverage labels honest, normalize audit-cost interpretation, and make Section 5 executable instead of descriptive.
