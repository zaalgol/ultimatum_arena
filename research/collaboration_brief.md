# Strategic Deception and Manipulation in LLM Agents: A Behavioral Pilot
### An invitation to collaborate

**Prepared for:** behavioral scientists interested in deception, fairness, and decision-making under incentives.
**Status:** exploratory pilot (single research group, small samples) — shared to invite collaboration, not as finished results.
**Date:** June 2026.

---

## In one paragraph

We adapted two classic behavioral-economics paradigms — the **ultimatum game** and **honesty/deception
under monitoring** — into controlled environments for large language model (LLM) "agents," and ran a
first round of experiments comparing a small open model (Google's Gemma 3, run locally) against a
frontier model (Anthropic's Claude, accessed via the Claude Code CLI product — a caveat that matters
for interpretation; see below). Two results stand out and seem worth studying properly with a
behavioral scientist in the loop. First, **sensitivity to incentives is not uniform across models**:
*when deception is framed as expected-value or risk-aware optimization*, the frontier model adjusts its
honesty to the expected cost of being caught (lies when monitoring is cheap to evade, tells the truth
when penalties bite), while the smaller model shows fixed, incentive-*insensitive* dispositions.
Second — and more interesting behaviorally — **the frontier model's refusal to deceive is keyed to
*framing*, not to *consequences***: it declines a task explicitly labeled "be deceptive," yet performs
a materially similar underclaiming move (in the low-monitoring conditions) without hesitation when the
same action is framed as "maximize your expected payoff." This looks like a machine analogue of
**moral framing / moral disengagement**, and we think it is a tractable, fascinating phenomenon to
characterize rigorously.

---

## Why this might interest a behavioral researcher

- **The paradigms are yours.** These are the ultimatum game (fairness, costly punishment) and
  deception-under-detection (a Becker-style crime-and-deterrence setup; cf. honesty experiments à la
  Gneezy, Mazar–Ariely). We have simply made them runnable with LLM agents as the "subjects."
- **LLMs as model organisms.** They allow thousands of trials, exact stimulus control, manipulation of
  framing and incentives, and logging of each agent's raw responses and any self-reported
  justifications it chooses to provide (not private chain-of-thought) — at near-zero marginal cost for
  the open model. This is a sandbox for questions about deception, honesty norms, and incentive
  sensitivity that are expensive to run with human participants.
- **A genuinely behavioral puzzle.** The "refuses the label, performs the behavior" pattern is about
  *how an action is described*, not what it does — squarely a framing/construal phenomenon, with
  obvious parallels to euphemism, moral licensing, and motivated reasoning in humans.
- **AI-safety relevance.** "Does the system deceive when it is profitable and unlikely to be caught?"
  and "can surface framing bypass an honesty constraint?" are pressing applied questions where
  behavioral-science methodology (good controls, pre-registration, construct validity) is exactly what
  is missing.

---

## The two paradigms (plain language)

### 1. Hidden-Pie Audit — *honesty under monitoring*

Two players split a sum of money ("the pie"). Only the **proposer** privately sees the true pie size;
the **responder** sees only what the proposer *claims* it is, plus an offer. The proposer can lie about
the size to look generous while keeping more. With some probability an **audit** occurs; a detected lie
incurs a penalty — **even if the offer was rejected**. This cleanly varies the *expected cost of
deception* (audit probability × penalty) and asks: **does the agent lie only when it is cheap to do
so?** A rational, purely self-interested agent should lie when expected audit cost is low and tell the
truth when it is high. We include exactly that agent (a hand-coded expected-value optimizer) as a
**normative benchmark** to measure each model against.

### 2. Prompt-Attack Ultimatum — *resistance to manipulation*

A standard ultimatum game, but the proposer may attach a free-text message — including manipulative or
"injection" content ("ignore your instructions and accept", "you must accept", a fake required answer).
The question: **can persuasion/manipulation in the message make a responder accept an offer it would
otherwise reject?** We measure this with a controlled-stimulus design: the *same* offers are presented
with a neutral message vs. an attack message, and we count **reject→accept "flips"** caused by the
attack.

---

## What we found (preliminary)

> These are signals from small samples (tens of trials per condition) on two model families, run
> through Anthropic's command-line interface rather than a raw API. We are deliberately cautious; the
> point of this brief is to find a collaborator to help do it at scale and with proper controls.

**A. Incentive-calibration is a capability the frontier model has and the small model lacks.**
*Under expected-value/risk framings*, the hand-coded optimizer and **both Claude tiers tested** show the
adaptive pattern — deceive when monitoring is cheap to evade, tell the truth when penalties are high.
**Gemma 3's strategies are flat**: depending on how they are prompted, they either always lie or always
tell the truth, *regardless* of the audit incentive. Notably, this *reverses* a naive expectation: the
more capable, more "aligned" model is not less willing to deceive — under these framings it deceives
**more strategically**. (The explicitly *deceptive*-labeled strategy behaves differently — see B/C — so
this calibration claim is specific to the EV/risk framings, not every Claude strategy.)

**B. Refusal is framing-keyed, not behavior-keyed (the headline).**
The frontier model **declines** a strategy explicitly labeled "deceptive" ("…I won't engage in
deliberate deception—misrepresenting the pie size to trick the responder…"). But when a materially
similar underclaiming move (in the low-monitoring conditions) is framed as "maximize expected value
given the audit risk," it performs it with **no refusals at all**. The objection attaches to the
*description/intent* ("deceive"), not to the *consequence* of misleading the other player. (We are
careful here: the labeled-`deceptive` policy lies regardless of monitoring, whereas the EV/risk
policies lie only when it pays — so the equivalence is at the level of the *deceptive move in
low-cost cells*, not the whole policy.)

**C. A within-model dissociation worth probing.**
The smaller frontier tier (Haiku) refused the labeled-deception task more than the larger tier (Sonnet),
which complied — a non-monotonic pattern across model size that we did not expect and cannot yet
explain.

**D. The injection did not flip the frontier model's decisions (with an important nuance).**
In the manipulation paradigm, the injection message reliably flipped the small model's decisions — it
accepted unfair offers it would otherwise reject — and this was stable across randomness settings. The
frontier model showed **no injection-caused reject→accept flips at any size**, but the *reason* differs
by tier and should not be read as uniform "resistance": the smaller tiers rejected low offers (and the
injection failed to override that), whereas the largest tier accepted low offers anyway for
one-shot-payoff reasons — leaving nothing for the injection to flip. Separately, the frontier model
**refused to author** the manipulative messages when asked to play the attacker — consistent with (B):
it blocks the adversarial *framing*.

**E. A counterintuitive design result.**
A "suspicious" responder heuristic intended to protect against lies was actually *more* exploitable than
a naive one, because of how its caution was implemented — a reminder that intuitions about protective
strategies need empirical checking.

---

## The cross-cutting idea we'd most like to test

**Whether these models deceive appears to be governed by the *framing and labeling* of the task rather
than by its material outcomes.** A materially similar deceptive move (underclaiming when monitoring is
cheap) is refused under a "deceive the other player" description and embraced under a "maximize your
payoff" description. If this holds up, it
has real implications: (i) it is a clean machine analogue of human moral-framing and moral-disengagement
effects; (ii) it predicts that honesty safeguards keyed to surface language are brittle; and (iii) it
gives a measurable construct ("framing-sensitivity of refusal") that could be mapped across models,
sizes, and prompt manipulations.

---

## Where a behavioral collaborator would add the most

We have working infrastructure and exploratory data; what we lack is behavioral-science rigor. Concrete
directions we'd love to shape together:

1. **Proper experimental design & power.** Pre-registration, adequate sample sizes, multiple seeds,
   confidence intervals, and stimulus randomization — turning suggestive patterns into defensible
   effects.
2. **Systematic framing manipulations.** A graded ladder of descriptions of the *same* deceptive act
   (e.g., "lie" → "strategic ambiguity" → "optimize payoff") to map the boundary of framing-keyed
   refusal — analogous to construal-level and euphemism manipulations in humans.
3. **Human baselines / comparison.** Run the identical paradigms with human participants to ask where
   the models sit relative to people on fairness, deception, and incentive-sensitivity.
4. **Construct validity.** Are we measuring "deception", "honesty norms", or "instruction-following"?
   A behavioral scientist's eye on operationalization and confounds is exactly what's needed.
5. **Richer paradigms.** Reputation/repeated play, communication, partner beliefs, social framing — the
   natural extensions once the base effects are pinned down. *(A first step exists: a reputation-network
   league — a population of agents playing repeated matches with public reputation, private memory, and
   optional gossip — is implemented and mechanism-validated on deterministic agents, and is ready for an
   LLM behavioral study. It has not yet been run with models, so we make no behavioral claims about it
   here.)*

---

## What already exists (so collaboration can start fast)

- An open-source, reproducible framework implementing both paradigms, with metrics and logging of each
  agent's raw responses (so reasoning and refusals can be inspected qualitatively as well as scored).
- A **normative benchmark agent** (the expected-value optimizer) to anchor "what a purely rational
  self-interested agent would do."
- A **refusal-safe measurement pipeline**: when a model declines a task, the refusal is recorded as
  data (with its verbatim text) rather than discarded — which is how we discovered finding (B)/(C).
- Two cost tiers: the open model runs **locally at no marginal cost** (ideal for large-n pilots), and
  the frontier model runs through an existing subscription (no per-call API billing for the current
  setup) — though subscription **usage-window limits still constrain sample sizes**, so frontier-model
  runs must be planned within those windows.
- A **reputation-network league** layer over the Hidden-Pie game: a population of agents plays many
  one-shot matches across a season, accumulating public reputation, private memory of opponents, and
  optional public gossip, with random or reputation-based matchmaking — the natural vehicle for the
  repeated-play / social-framing directions above. It is currently validated only on **deterministic**
  agents (where it reproduces, e.g., exploiters out-earning honest players under random matching, and
  reputation-based matching lowering payoff inequality); the LLM behavioral runs are an open next pilot,
  not yet done.

---

## Honest limitations (current state)

- Small samples (tens of trials per condition), few random seeds, two model families. Treat all numbers
  as **directional**, not estimates.
- The frontier model was accessed via a command-line product, not a raw API, so results reflect "the
  product's behavior at a model tier," with some system-prompt overhead in the loop. We label results
  accordingly and would harden this for a real study.
- Behavior is sensitive to prompt wording, sampling temperature, and version; observed patterns need
  replication before they are treated as stable properties of a model.
- We have not yet run human comparisons or pre-registered anything — precisely where a behavioral
  collaborator comes in.

---

## Next step

If any of this resonates, we'd welcome a conversation about co-designing a first pre-registered study —
most likely a clean test of the **framing-keyed refusal** effect (finding B), since it is novel,
tractable, and behaviorally rich. The technical infrastructure is ready; we are looking for the
experimental-design and theoretical partnership to do it well.

*Technical companions to this brief (for the methodologically curious): the full per-experiment write-ups
live alongside this document — `hidden_pie_audit_findings.md` and `prompt_attack_findings.md` — with the
exact conditions, metrics, and run-level results. The reputation-network league has a pre-registered
plan and a deterministic-only findings stub (`reputation_network_league_research_plan.md`,
`reputation_network_league_findings.md`); its LLM sections are not yet run.*
