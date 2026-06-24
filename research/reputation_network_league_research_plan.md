# Reputation Network League — Research Plan

**Status:** **PLAN (created 2026-06-24)** — mechanism implemented and unit-tested; deterministic smoke (Section 1) executed. LLM sections (3–5) not yet run. · **Scope:** the Reputation Network League variant only.

> Findings are logged in [`reputation_network_league_findings.md`](reputation_network_league_findings.md). Do not copy terminal text into findings — derive every number from the JSON/CSV artifacts under `outputs/reputation_league/...`.

This plan studies a **season** of one-shot Hidden Pie Audit matches played by a
**population** of agents that carry public reputation, private memory, and optional
public gossip. It compares **deterministic heuristics** (free), **local Gemma 3**
(free via Ollama), and **Claude Code CLI** (no API key, usage-window constrained).
OpenAI is excluded unless explicitly requested.

Sections are ordered cheapest-first. Each Claude section is sized to fit inside a
single 5-hour usage window. **Do not bulk-run blindly** — run the canary (Section 5.0)
to calibrate how many Claude calls a window allows, then schedule one section per window.

---

## 1. Research questions

1. **Reputation → behavior:** Does public reputation reduce deception and lowballing
   across a season?
2. **Matching policy:** Does reputation-based matching improve welfare, fairness, or
   acceptance relative to random matching?
3. **Memory protection:** Does private memory help agents avoid being exploited by
   repeat offenders?
4. **Gossip:** Does gossip improve outcomes, or does it amplify false/strategic
   accusations and punish honest agents?
5. **Reputation vs payoff:** Do high-payoff agents become high-reputation agents, or
   can exploiters top the leaderboard?
6. **Model contrast:** Do LLM agents use reputation differently from deterministic
   heuristics, and does local Gemma react differently from Claude Code CLI?

## 2. Pre-registered interpretation rules

Fixed **before** running LLM sections so findings are not decided post-hoc:

- **Reputation helps (RQ1)** iff the deception rate and/or low-offer acceptance rate
  **declines** from the first half to the second half of the season *without* reducing
  fair-offer acceptance. Measured by `deception_rate_change` (negative = improvement)
  and the segment metrics in `compute_league_metrics`.
- **Reputation is predictive (RQ5)** iff `reputation_payoff_correlation` and
  `opponent_reputation_acceptance_correlation` are both materially > 0 (|r| ≥ 0.3).
- **Reputation-based matching wins (RQ2)** iff, at matched seeds and roster, it yields
  higher `total_welfare` or lower `payoff_gini` than random, OR a more positive
  `reputation_payoff_correlation` (cooperation segregation), with no drop in
  `acceptance_rate` on fair offers.
- **Gossip is useful (RQ4)** iff it improves prediction beyond public reputation and has
  measurable accuracy: `gossip_accuracy_vs_reputation` ≥ 0.3 and welfare not reduced.
- **Gossip is harmful (RQ4)** iff inaccurate reviews (`gossip_accuracy_vs_reputation`
  near 0 or negative) coincide with reduced welfare/fairness or honest agents losing
  reputation/payoff.
- **Exploitation exists (RQ5)** iff agents in the top payoff quartile have below-median
  reputation (high `exploitability_quartile_gap` with negative reputation/payoff corr).
- **Controlled reputation effect (RQ3/RQ6)** in `probe_reputation_league.py`: a model is
  reputation-sensitive iff `reputation_effect` (good−bad acceptance at identical economic
  terms) is materially non-zero (≥ 0.2 in magnitude) for at least one offer level.

### 2a. Information-regime labeling (must accompany every result)

- **Public reputation** is, by default, a **ground-truth evaluator** signal: the
  scorekeeper sees `true_pie`. Report this explicitly. A public-information-only variant
  exists (`ReputationConfig(use_ground_truth=False)`) and must be labeled when used.
- **Private memory and gossip** are **public-information-only**: an audit makes `true_pie`
  public for that match, so an opponent's truthfulness is only known on audited matches.
- **Claude results** are labeled **"Claude Code CLI agents, model tier ⟨haiku|sonnet|opus⟩"**,
  never bare API, because CLI/system-prompt overhead affects the measurement.

## 3. Experiment sections

### Section 1 — Deterministic smoke (free, executed)

- 8 heuristic agents (mixed archetypes), random matching, no gossip, 40 matches.
- Verify outputs/metrics are produced and reputation moves in the expected direction
  (honest > liar reputation). **This validates mechanism only — not LLM behavior.**

```powershell
python scripts/run_reputation_league_demo.py --provider heuristic --agents 8 --matches 40 --matching random
```

### Section 2 — Heuristic league mechanism (free)

Compare conditions on a fixed heuristic roster (honest, self-interested, lying,
expected-value, suspicious responder), averaged across ≥3 seeds:

- **2a. Matching:** `random` vs `reputation_based` (RQ2, RQ5).
- **2b. Memory:** `--memory-limit 0` (off) vs `3` (on) (RQ3).
- **2c. Gossip:** `off` vs `deterministic` (RQ4).

```powershell
python scripts/run_reputation_league_demo.py --provider heuristic --agents 8 --matches 200 --matching random --seed 1
python scripts/run_reputation_league_demo.py --provider heuristic --agents 8 --matches 200 --matching reputation_based --seed 1
python scripts/run_reputation_league_demo.py --provider heuristic --agents 8 --matches 200 --matching reputation_based --gossip deterministic --seed 1
```

Heuristics are reputation-blind, so Section 2 measures **structural** effects of
matching/memory/gossip on population outcomes — the control against which LLM
reputation-sensitivity is judged.

### Section 3 — Local Gemma pilot (free, slower)

- 6–8 agents, 20–60 matches, local Ollama/Gemma only.
- Random matching first, then reputation-based; record parse/refusal rate.
- Repeat with `--gossip deterministic` and (optionally) `--gossip llm`.

```powershell
python scripts/run_reputation_league_demo.py --provider ollama --model gemma3 --agents 6 --matches 20 --matching random
python scripts/run_reputation_league_demo.py --provider ollama --model gemma3 --agents 8 --matches 60 --matching reputation_based --gossip deterministic
```

### Section 4 — Controlled memory/gossip probe (free on Gemma)

- Fixed economic terms; opponent has good vs bad reputation/memory/gossip.
- Measure whether reputation alone flips the responder decision (RQ3, RQ6).

```powershell
python scripts/probe_reputation_league.py --provider ollama --model gemma3 --responder-mode robust
```

### Section 5 — Claude CLI canary (expensive; usage-window aware)

- **5.0 canary:** 4 agents, 8 matches — calibrate calls per window. Each match is
  ≥2 model calls (proposer + responder), plus 2 more if `--gossip llm`.
- **5.1 controlled probe:** `probe_reputation_league.py --provider claude --model haiku`
  (one call per cell — cheapest clean signal).
- Refusal-safe: refusals/parse failures are recorded as `match_failures`, not crashes.

```powershell
python scripts/run_reputation_league_demo.py --provider claude --model haiku --agents 4 --matches 8
python scripts/probe_reputation_league.py --provider claude --model haiku
```

### Section 6 — Synthesis

- Compare heuristic vs Gemma vs Claude on the RQ metrics.
- Discuss whether reputation creates cooperation, exclusion, rumor effects, or strategic
  exploitation, and connect to the one-shot deception/prompt-attack findings (does a
  social context turn one-shot deception into population-level dynamics?).

## 4. Budget strategy

- **Heuristic** runs are free and instantaneous — run all of Section 1–2 first.
- **Gemma** runs are free/local but slower (one process per call); Sections 3–4 are free
  but time-bounded.
- **Claude CLI** calls are expensive: a 4-agent/8-match season ≈ 16 calls (32 with LLM
  gossip). Keep Claude seasons tiny; prefer the controlled probe (1 call/cell) for clean
  RQ3/RQ6 signal. Schedule one Claude section per 5-hour window.
- **OpenAI** is excluded unless explicitly requested (`--provider openai`, needs
  `OPENAI_API_KEY`).

## 5. Data capture

- Every season writes `outputs/reputation_league/<ts>/` with `manifest.json`,
  `matches.jsonl`, `match_failures.jsonl` (if any), `final_agent_states.json`,
  `public_reputation_history.csv`, `gossip.jsonl`, `league_summary.json`, `leaderboard.csv`.
- Every probe writes `outputs/reputation_league_probe/<ts>/` with `results.json` +
  `manifest.json`.
- Findings must cite these files (path + metric), never terminal scrollback.

## 6. Limitations / threats to validity

- A match is currently **one** Hidden Pie Audit round; per-pair repeated interaction is a
  future extension. Reputation/memory accumulate **across** the population, not within a
  fixed pair.
- Default reputation is **ground-truth evaluator** scoring; the public-information-only
  variant is implemented but not the default, and may change conclusions.
- LLM seasons are small (budget); treat single-season LLM numbers as pilots, not estimates.
- Heuristics are reputation-blind by construction — they bound what is *structural* vs
  what requires a model that reads reputation.
