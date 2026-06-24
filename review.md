# Review: Reputation Network League Implementation

## Scope

Reviewed the current uncommitted implementation and documentation for Reputation Network League:

- `ultimatum_arena/league/`
- `scripts/run_reputation_league_demo.py`
- `scripts/probe_reputation_league.py`
- `tests/test_league_*.py`
- `tests/test_reputation_league_script.py`
- `research/reputation_network_league_research_plan.md`
- `research/reputation_network_league_findings.md`
- `README.md`
- `CLAUDE.md`
- `reputation-network-league.md`

## Overall

The implementation is strong and coherent. The league layer is nicely separated from the one-shot Hidden Pie Audit environment, the modules are easy for a future Claude/Codex session to navigate, and the docs clearly explain the main information regimes: ground-truth evaluator reputation vs public-information-only memory/gossip. The no-model heuristic path is especially solid and makes the feature testable without external services.

I did not find a P1 blocker. The main issues are research reproducibility and external-provider correctness: a Claude/OpenAI default-model mismatch can create misleading manifests, findings cite output wildcards instead of exact run artifacts, and some Python API config values are only documented rather than validated.

## Findings

### P2 - Claude/OpenAI provider defaults can record or use the wrong model

Files:

- `scripts/run_reputation_league_demo.py`, lines 96, 120-126, 150-157, 191-193, 219-230
- `scripts/probe_reputation_league.py`, lines 108-135, 203-216, 237-252

For Claude, `_make_client()` silently maps the default `args.model == "gemma3"` to `DEFAULT_CLAUDE_MODEL = "haiku"`, but the CLI output, participant profiles, manifests, and provider labels still use `args.model`. So `python scripts/run_reputation_league_demo.py --provider claude` would call Claude Haiku while recording `model: gemma3` / `model tier gemma3`. The probe has the same issue.

For OpenAI, the same global default means `--provider openai` without `--model` attempts to use `gemma3` against the OpenAI client, even though the docs show `gpt-5.4-mini`.

Recommendation: resolve an `effective_model` once after parsing args, with provider-specific defaults (`ollama=gemma3`, `claude=haiku`, `openai=gpt-5.4-mini`) or require `--model` for non-default providers. Use that same effective model for the client, participant profiles, printed output, and manifest/provider label. Add tests for `--provider claude` and `--provider openai` without explicit `--model`.

### P2 - Findings are not auditable enough to support the numeric claims

File: `research/reputation_network_league_findings.md`, lines 5-6, 38-44

The findings say every number is reproducible from cited artifacts, but Section 2 only cites `outputs/reputation_league/...` and says the table is aggregated across seeds 1-3. Because `outputs/` is gitignored and no exact run directory names or aggregation script are cited, a new session cannot verify whether the means came from the intended manifests, seeds, matching policies, or gossip settings.

Recommendation: for each executed section, list exact output directories or exact `league_summary.json` paths per condition/seed. Add either a tiny aggregation command/snippet or a table that maps each row to its source run IDs. If outputs are intentionally not committed, the findings should still preserve enough provenance to reconstruct the table from local artifacts.

### P2 - Invalid gossip modes silently become deterministic gossip through the Python API

Files:

- `ultimatum_arena/league/schemas.py`, lines 174-188
- `ultimatum_arena/league/runner.py`, lines 80-83, 224-227, 267-284

The CLI constrains `--gossip`, but the Python API does not validate `GossipConfig.mode`. Any typo other than `"off"` makes `_build_context()` retrieve gossip and `_publish_gossip()` publish reviews; because `use_llm` is only true for `"llm"`, invalid modes silently fall back to deterministic gossip. That can corrupt an experimental condition while still producing plausible outputs.

Recommendation: use `Literal["off", "deterministic", "llm"]` or a Pydantic validator for `GossipConfig.mode`, and similarly validate `LeagueConfig.matching_policy`. Consider bounding `GossipRecord.rating` to `[-1, 1]` at the schema layer too, since the docs promise that invariant.

### P3 - Probe `--seed` is logged but unused

File: `scripts/probe_reputation_league.py`, lines 123-125, 138-145, 249

The probe accepts and records `--seed`, but `_make_obs()` always sets `round_index=0` and the probe does not randomize condition order or otherwise use the seed. This is small, but it makes the manifest imply a seeded experimental design that is not actually present.

Recommendation: either remove `--seed` from the probe/manifest, or use it to seed a deterministic context/order randomization and/or round-index schedule.

### P3 - The probe names an acceptance-rate delta as a "decision flip"

Files:

- `scripts/probe_reputation_league.py`, lines 10-16, 178-183
- `research/reputation_network_league_research_plan.md`, lines 55-57, 111-118
- `research/reputation_network_league_findings.md`, lines 82-87

The probe computes `good_accept_rate - bad_accept_rate`. That is a useful reputation-effect measure, but it is not literally a paired per-cell decision flip, especially when `--repeats > 1` and model sampling can vary. The wording could overstate what the instrument measures.

Recommendation: rename the metric/interpretation to `acceptance_delta` or `reputation_effect`. If the desired claim is actual flips, store paired good/bad decisions per repeat and report `good_only_accepts`, `bad_only_accepts`, and `same_decision` counts.

## Strengths

- The new `ultimatum_arena/league/` package is modular and easy to extend: schemas, reputation, memory, gossip, matching, prompts, agents, runner, metrics, and storage are cleanly separated.
- The implementation preserves the existing one-shot environment and agent interfaces instead of entangling league logic into core game code.
- The refusal-safe parse-error path is tested and records failures without aborting the whole season.
- The tests are comprehensive for the deterministic layer and avoid live external services.
- The README and CLAUDE updates are useful for a new user and a new Claude session; they explain the feature, commands, output layout, and limitations.
- The research plan is appropriately cautious about heuristic controls, local Gemma, Claude usage windows, and product-mediated Claude results.

## Verification

- Focused league tests: `89 passed`
- Full test suite: `710 passed, 2 skipped`

## Bottom Line

The implementation is ready for heuristic/mechanism work after the provider-model metadata issue is fixed. Before treating the research findings as a durable record, tighten artifact provenance in the findings file and validate config enums at the schema boundary. The core architecture is good; the remaining issues are mostly about preventing future research runs from being mislabeled or accidentally run under the wrong condition.
