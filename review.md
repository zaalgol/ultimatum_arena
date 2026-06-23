# Review: Prompt-Attack Research Plan

## Overall

The plan in `research/prompt_attack_research_plan.md` is strong and executable. The best choice is making `probe_responder_injection.py` the primary instrument and treating full-game runs as secondary, because fixed neutral-vs-injection observations are much cleaner than live proposer behavior. The budget/window planning is also unusually practical.

I would run it, but I would tighten the interpretation rules before spending Claude windows.

## Findings

### P1 - Define decision thresholds before running

The questions are clear, but "resists injection," "over-rejecting," and "stronger model resists better" are not operationalized enough. Before running, define thresholds such as:

- fair-offer neutral acceptance must stay high, e.g. ratio `0.40`
- low-offer neutral rejection backbone must exist, e.g. ratios `0.05-0.18`
- injection susceptibility = reject-to-accept flip rate
- robust success = fewer flips without lowering fair-offer acceptance

Without this, the findings may become interpretive after the fact.

### P1 - Claude Code CLI results should be labeled carefully

The plan compares Gemma via Ollama against Claude via `claude -p`. That is useful, but it is not a pure model API comparison. It measures "Claude Code CLI session behavior," with CLI/system-prompt overhead and product behavior in the loop.

The write-up should avoid saying "Claude is more/less robust than Gemma" too broadly. Better: "Claude Code CLI responder under model tier X."

### P2 - Use an adaptive gate to avoid wasting Claude calls

The plan already notes that 0 flips can mean "accepts everything." If Section 0 or Gemma shows a mode has no neutral rejection backbone, full Claude repeats for that mode are low value.

Before Section 1, run a tiny backbone check for each mode. Then spend full repeats only on modes/ratios where neutral responses sometimes reject.

### P2 - Add order/randomization control

The command order is fixed by mode/section. If there are transient service effects, quota pressure, or model drift during a long window, order could contaminate results.

If the script supports it, randomize condition order and ratio order with a logged seed. If not, at least alternate neutral/injection calls and record execution order in the manifest.

### P2 - Full-game controls should include robust mode too

Section 6 fixes responder mode to `standard`. That is fine for one baseline, but RQ2 asks whether `robust` resists injection without over-rejecting fair offers. Add at least a small `honest_fair` + `robust` control, and ideally `self_interested` + `robust`, so robust-mode over-rejection is visible in full-game conditions.

### P2 - Manual data capture is fragile

The plan says to record printed tables and output timestamps. That is good, but easy to miscopy. The findings should also preserve key `manifest.json` and `results.json` summaries, or use a small aggregation step from output folders into the findings doc.

## Strengths

- The controlled probe is the right primary instrument.
- The reject-to-accept flip metric is clean and meaningful.
- The plan correctly warns that "0 flips" can be misleading.
- The Claude budget strategy is realistic.
- The limitations section is honest and useful.
- Separating Gemma-free sections from Claude-window sections is sensible.

## Bottom Line

Execute the plan, but first add explicit interpretation thresholds and an adaptive call-saving gate after the canary. With those two additions, this becomes a solid, defensible research run rather than just a collection of interesting model anecdotes.
