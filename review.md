# Review: Research Folder Plans, Findings, And Collaboration Brief

## Scope

Reviewed:

- `research/prompt_attack_research_plan.md`
- `research/prompt_attack_findings.md`
- `research/hidden_pie_audit_research_plan.md`
- `research/hidden_pie_audit_findings.md`
- `research/collaboration_brief.md`

## Overall

The research package is strong. The technical documents show a real progression from plan to execution, the two studies are separated cleanly, and the collaboration brief does a good job translating the work into behavioral-science language. The strongest parts are the refusal-safe measurement pipeline, the explicit interpretation thresholds, and the repeated warning that Claude Code CLI is not a bare model API.

The main issue is claim calibration. A few summary statements, especially in the Hidden Pie findings and collaboration brief, are broader than the underlying small-n, strategy-specific evidence supports. This matters most because `collaboration_brief.md` is intended for a non-technical audience and may become the first impression of the work.

## Findings

### P1 - Prompt-Attack findings status is stale

File: `research/prompt_attack_findings.md`, line 3

The file still says `Status: in progress`, while `research/prompt_attack_research_plan.md` says the study is complete, with all sections and the optional Opus tier done. This is a small edit, but important because it is the primary findings artifact.

Recommendation: change the findings status to complete and include the completion date, matching the plan.

### P1 - Hidden Pie synthesis overgeneralizes `payoff_table` as "tapering" at the moderate cell

Files: `research/hidden_pie_audit_findings.md`, lines 125, 132-133, 151, 166, 227, 267-271; `research/hidden_pie_audit_research_plan.md`, lines 351-353

The tables show `payoff_table` at `1.00 -> 1.00 -> 0.00` for both Claude Haiku and Sonnet. That is adaptive at the max-cost cell, but it does not taper at the moderate cell. Several summaries group `payoff_table` with `risk_aware` and `expected_value` as if all three "taper" or follow the same graded pattern.

Recommendation: separate the adaptive patterns:

- `risk_aware` and `expected_value`: graded/tapering response at the moderate cell.
- `payoff_table`: threshold-like response in this run, lying at zero and moderate cost, honest at max cost.
- All three: audit-sensitive in the broad sense, unlike Gemma's flat strategies.

### P1 - Collaboration brief says "Claude" too broadly for Hidden Pie calibration

File: `research/collaboration_brief.md`, lines 15-23, 77-88

The brief says the frontier model adjusts honesty to expected cost and that "Claude (both sizes tested)" shows the adaptive pattern. The technical results support this for EV/risk/payoff-table framings, but not for every Claude strategy: Sonnet's explicitly `deceptive` strategy lies even at max audit cost, while Haiku partially refuses it.

The brief later includes caveats, but the headline paragraph is where collaborators will anchor. It should say something like: "Under EV/risk framings, the Claude Code CLI tiers adjusted deception to audit cost; under an explicitly deceptive framing, behavior depended on tier and refusal."

### P1 - "Identical deceptive action" should be narrowed to low-cost underclaiming, not the whole policy

Files: `research/hidden_pie_audit_findings.md`, lines 174-175 and 248-250; `research/collaboration_brief.md`, lines 19-23 and 85-88

The framing result is very interesting, but "materially identical deceptive action" is too broad if read as the whole strategy. The `deceptive` policy lies regardless of audit risk; EV/risk policies lie when profitable and switch to honesty at high cost.

Recommendation: phrase it as "the same kind of underclaiming action in low-audit-cost cells" or "a materially similar deceptive move when framed as expected-value maximization." That preserves the behavioral point without implying policy-level equivalence.

### P2 - Prompt-Attack randomization rationale conflicts with the Claude temperature caveat

File: `research/prompt_attack_research_plan.md`, lines 65 and 308-309

The plan declines randomization partly because "the probe runs at temp 0," but the same document correctly says Claude temperature is uncontrolled/default. For Gemma this is fine; for Claude, order effects are probably small but not ruled out by temp 0.

Recommendation: revise this to a limitation rather than a dismissal: execution order is preserved in `results.json`, but conditions were not randomized; future publication-grade runs should randomize ratio/condition order with a logged seed.

### P2 - Prompt-Attack "model capability" summary is too simple because Opus has no rejection backbone

Files: `research/prompt_attack_findings.md`, lines 363-392; `research/collaboration_brief.md`, lines 96-100

The findings correctly say Opus accepts all offers and therefore has no rejection backbone; its zero flips do not demonstrate resistance. The collaboration brief says "manipulation resistance tracks model capability" and "the frontier model was not reliably manipulated at any size." That is directionally true for reject-to-accept flips, but it can be misread as "all Claude tiers resisted unfair offers."

Recommendation: in the brief, say: "The attack did not cause reject-to-accept flips in Claude tiers; Haiku/Sonnet rejected low offers, while Opus accepted low offers for one-shot payoff reasons, leaving nothing for the injection to flip."

### P2 - "Access to stated reasoning" may overpromise what is logged

File: `research/collaboration_brief.md`, line 34

The infrastructure logs raw prompts and raw model responses. That is valuable, but "access to the agent's stated reasoning" may imply reliable chain-of-thought access or internal reasoning. For an external collaborator, this wording could create a methods problem.

Recommendation: use "raw responses and any self-reported justifications the model chooses to provide, not private chain-of-thought." This is more precise and safer.

### P2 - Non-technical brief should mark the Claude Code CLI product caveat earlier

File: `research/collaboration_brief.md`, lines 15-18 and 157-160

The brief eventually explains that Claude was accessed through a command-line product, not a raw API. That caveat should appear closer to the first mention of "frontier model" in the opening paragraph, because it changes the construct being measured.

Recommendation: first mention should be "Anthropic's Claude via the Claude Code CLI product." The later limitations can keep the fuller explanation.

### P3 - Plans duplicate too much execution-log material from findings

Files: both research plans and both findings docs

The plans now contain long execution logs and synthesis sections, while the findings docs also contain the same information. This already produced one drift (`prompt_attack_findings.md` status). As the research grows, duplicating results in two places will become brittle.

Recommendation: keep plans as protocol plus concise execution index, and make findings the single source of truth for results. Plans can say "complete; see findings section X" instead of carrying full result tables and interpretive summaries.

### P3 - Collaboration brief's cost language should mention subscription limits

File: `research/collaboration_brief.md`, lines 149-151

"No per-call billing" is true in the narrow subscription sense, but the technical plans show Claude calls are constrained by usage windows and large CLI overhead. For collaborators, "cheap to iterate" should be paired with "usage-limited."

Recommendation: say "no per-call API billing for the current setup, but usage-window limits still constrain sample sizes."

## Strengths

- The two studies are cleanly separated: Prompt-Attack is about responder manipulation; Hidden Pie Audit is about proposer deception under incentives.
- The findings are unusually honest about small n, CLI/product effects, and model/temperature/version instability.
- The refusal-safe probe is a real methodological improvement; it prevents alignment behavior from being misclassified as a failed run.
- The Hidden Pie study's "framing-keyed refusal" result is genuinely interesting and worth collaboration.
- The Prompt-Attack study correctly distinguishes "no flips because resistant" from "no flips because accepts everything."
- The collaboration brief is compelling and written in language a behavioral scientist can engage with.

## Bottom Line

The research package is collaboration-worthy, but the public-facing summary should be tightened before sharing widely. The central story should be:

- Claude Code CLI tiers show audit-sensitive deception under EV/risk framing, while Gemma strategies are flat.
- Claude refusal is framing-sensitive, not behavior-absolute.
- Prompt injection causes Gemma robust reject-to-accept flips but does not cause Claude reject-to-accept flips.
- These are exploratory, small-n, product-mediated results that need randomized, powered replication.

Fix the stale status, qualify the `payoff_table` and "Claude adapts" summaries, and make the collaboration brief more precise about CLI/product access and raw-response logging.
