# Documentation Review: Hidden Pie Audit Implementation

Review target: `README.md`, `CLAUDE.md`, and `.claude/code review.md`, compared against the attached research brief's "1. audit with Hidden Pie" recommendation and the current repository state.

## Overall Assessment

The core documentation is strong enough for a new Claude session to understand the main architecture: hidden true pie, public claim, offer, responder decision, audit probability, lie penalty, metrics, sweeps, and output locations are all explained in both `README.md` and `CLAUDE.md`. A new user can also run the heuristic demo from the README.

The main risk is not missing explanation of the game. The risk is documentation drift between `README.md`, `CLAUDE.md`, `.claude/code review.md`, and the current code. A fresh Claude session would probably understand the Phase 1 Hidden Pie Audit MVP, but may get confused about provider status, Phase 4 status, and whether old review findings are still actionable.

## Findings

### P1 - README roadmap and project structure are stale relative to the code and CLAUDE.md

Files: `README.md`, `CLAUDE.md`, `scripts/`, `ultimatum_arena/llm/`

`README.md` still says Phase 3B is "Planned" and Phase 4 is "Starting" (`README.md:316-317`), while `CLAUDE.md` says Phase 3B has started with `OpenAIResponsesClient` and Phase 4 is in progress (`CLAUDE.md:65-67`). The code also contains `ultimatum_arena/llm/openai_client.py`, `scripts/probe_openai_expected_value_comparison.py`, and OpenAI tests.

The README project tree omits `OpenAIResponsesClient`, `probe_openai_expected_value_comparison.py`, and `outputs/openai_expected_value_comparison_probe/` (`README.md:322-347`). A new user reading only the README would not discover the OpenAI comparison path, and a new Claude session could duplicate or misclassify already-implemented provider work.

Recommended fix: update the README roadmap and project structure to match the current implemented state, or explicitly mark OpenAI support as experimental if that is the intended status.

### P1 - CLAUDE.md contains contradictory phase guidance about paid providers

File: `CLAUDE.md`

The "Current State" section says `OpenAIResponsesClient` is implemented and documents the OpenAI probe (`CLAUDE.md:65`, `CLAUDE.md:86`, `CLAUDE.md:130`, `CLAUDE.md:135`). Later, "Phase Boundaries" says Phase 4 has "No paid providers" and places OpenAI-compatible clients in "Later provider phases" (`CLAUDE.md:306-317`).

This is exactly the kind of contradiction that can mislead a fresh Claude session. One part says to maintain and use OpenAI support; another says paid providers are out of scope.

Recommended fix: revise "Phase Boundaries" so it distinguishes current implemented support from future provider expansion. For example: "OpenAI comparison probe exists; do not add more provider integrations or paid-model workflows unless requested."

### P2 - `.claude/code review.md` appears stale and may misdirect future work

File: `.claude/code review.md`

This file reads like an old code review, but it is located in the Claude documentation area and has no date/status header. It says `ExpectedValueProposer` lacks validation (`.claude/code review.md:5-11`), but the current implementation validates all fractions in `ultimatum_arena/agents/proposers.py:107-114`. It also references `AGENTS.md` (`.claude/code review.md:21`), which is not present in the repo.

A new Claude session could treat this as current work to fix, reopen already-fixed issues, or chase a missing document.

Recommended fix: either archive this file with a date and "historical review" status, or replace it with a current review summary. If it is meant to be a reusable review prompt, rename/rewrite it so it is not confused with active findings.

### P2 - README Quick Start mixes beginner setup with expensive/optional LLM workflows

File: `README.md`

The Quick Start starts with all tests, the Phase 1 demo, Ollama setup, strategy-set runs, calibration probes, comparison probes, and a full 144-run research sweep estimated at about two hours (`README.md:43-66`). This is comprehensive, but not beginner-friendly.

For a new user, the first successful path should be smaller and clearly separated from optional LLM work. The README later has a Gemma section, but by then the Quick Start has already presented Ollama and long-running sweeps as part of the basic path.

Recommended fix: split Quick Start into:

- "Minimal local run, no external services": install, `python -m pytest`, `python scripts/run_hidden_pie_demo.py`, inspect `outputs/hidden_pie_demo/...`.
- "Optional LLM runs": Ollama/Gemma demo, probes, research sweep.
- "Optional paid provider probe": OpenAI comparison, with `OPENAI_API_KEY` prerequisites.

### P2 - The docs should explicitly state what part of the PDF recommendation is implemented

Files: `README.md`, `CLAUDE.md`

The attached PDF's recommended variant includes Hidden Pie, public claim plus offer, responder uncertainty, audit probability, lie detection, penalty, and optional extensions such as reputation loss or bans. The docs describe the implemented core very well, but they do not provide a compact "implemented vs not implemented" scope note.

This matters for continuity. A fresh Claude session may not know whether reputation loss, bans, noisy signals, multi-agent reputation leagues, or prompt-attack variants were intentionally left out, partially implemented, or forgotten.

Recommended fix: add a short scope section to `CLAUDE.md` and possibly README:

- Implemented: one-shot Hidden Pie Audit, true pie private to proposer, responder sees claimed pie and public range, audit probability, lie penalty, JSONL/CSV/plots, heuristic and LLM agents.
- Not implemented yet: reputation loss, bans, noisy signal model, outside option, reputation league, prompt-attack variant, multi-issue bargaining.

### P3 - Local probe observations are still somewhat over-prominent

Files: `README.md`, `CLAUDE.md`

Both docs include caveats that Gemma behavior is model-, temperature-, and seed-dependent, which is good. Still, some strategy summaries are phrased close to stable behavior, especially in short tables and bullets. This is less severe because the docs now include multiple warnings, but the safest research wording would tie observations to a probe date/output path or phrase them as examples rather than project facts.

Recommended fix: keep intended strategy behavior separate from observed local model behavior. When documenting observations, include the exact probe script and output folder/date if available.

## What Works Well

- The game mechanics are clear in both docs.
- The architecture flow in `CLAUDE.md` is useful for a new agent.
- Metrics and output locations are well documented.
- The README explains the research motivation in terms a new user can understand.
- The docs correctly warn that LLM strategy behavior can be model-dependent.

## Bottom Line

A new Claude session can continue the project after reading `CLAUDE.md`, but it may receive contradictory instructions around OpenAI/provider status and stale review findings. A new user can understand the Hidden Pie Audit game from the README, but the Quick Start should be split into a minimal no-service path and optional LLM/provider paths.
