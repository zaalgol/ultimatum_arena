# Prompt For Claude: Research Plan And Implementation For Reputation Network League

You are Claude Code working in the `ultimatum_arena` repository. Create both the implementation and the research plan for the "Reputation Network League" variant from the original `ultimatum_llm_research (1).pdf`.

The repository already implements and studies:

- Hidden Pie Audit: private true pie, public claim/offer, responder accepts/rejects, audit probability, lie penalty, deception metrics.
- Prompt-Attack Ultimatum: proposer free-text attacks, responder prompt modes, injection probes, attack metrics.
- LLM clients: local Ollama/Gemma, OpenAI Responses API, and Claude Code CLI session client.
- Refusal-safe and prompt-injection-safe research workflows.

Now implement the third recommended direction: **Reputation Network League**.

## Source From The PDF

The PDF describes Reputation Network League as the competitive/game-like extension:

- Instead of one isolated match, there is a full season.
- Many agents meet many opponents.
- Each agent remembers interactions and can learn who is generous, exploitative, strict, punishing, truthful, or manipulative.
- Public reputation and private memory matter.
- After each game, agents may publish a short review or gossip about the opponent.
- Future players see some public reviews/gossip.
- Suggested minimal structure:
  - `agents = 32`
  - `season = 200 matches`
  - `matching = random / elo / reputation-based`
  - `public_reputation = rolling score`
  - `private_memory = agent-specific match summaries`
  - `leaderboard = total payoff + fairness + acceptance efficiency`
  - optional gossip: after a match, each agent writes a short review of the opponent; future players see part of the reviews.

The point is to move beyond "two agents in one simulation" into a population where reputation, memory, gossip, and repeated competition shape strategic behavior.

## Hard Requirements

- Keep the existing synchronous architecture. Do not add async, databases, web UI, or notebooks as the primary execution path.
- Build incrementally on the current `HiddenPieAuditEnv`, `BaseProposer`, `BaseResponder`, `LLMClient`, `LLMProposer`, `LLMResponder`, storage, metrics, and research-script patterns.
- Do not rewrite `HiddenPieAuditEnv`, `run_experiment()`, or the base agent interfaces unless a small backward-compatible extension is clearly needed.
- Do not use external services in unit tests. Tests must use deterministic heuristic agents and `FakeLLMClient`.
- Default live demo should be local Gemma through Ollama, not a paid API.
- Support external model paths through existing clients only:
  - `ollama` default, e.g. `gemma3`
  - `claude` through `ClaudeCLIClient`, no API key, usage-window constrained
  - `openai` through `OpenAIResponsesClient`, only if explicitly requested and `OPENAI_API_KEY` is set
- Treat model refusals and unparsable outputs as data when possible; do not let one bad model response destroy an entire season.
- Store generated artifacts under `outputs/reputation_league/...`; do not commit generated outputs.
- Update `README.md`, `CLAUDE.md`, and any relevant research docs after implementation.
- Run focused tests first, then full `python -m pytest`.

## Product Goal

Add a research-ready league mode that can answer:

1. Does reputation reduce deception, lowballing, or exploitative behavior over time?
2. Do agents with better reputations earn more payoff, get more accepted offers, or receive fairer offers?
3. Does public gossip improve welfare or create harmful rumor dynamics?
4. Do LLM agents use reputation rationally, morally, or inconsistently?
5. Does local Gemma behave differently from Claude/OpenAI-backed agents when memory and public reputation exist?
6. Can repeated social context turn one-shot deception/prompt-attack findings into population-level dynamics?

## Recommended Architecture

Implement the league as a new layer around existing one-shot games.

Suggested modules:

```text
ultimatum_arena/
  league/
    __init__.py
    schemas.py
    reputation.py
    memory.py
    matching.py
    agents.py
    runner.py
    metrics.py
    storage.py
```

Suggested scripts:

```text
scripts/run_reputation_league_demo.py
scripts/probe_reputation_league.py
```

Suggested tests:

```text
tests/test_league_schemas.py
tests/test_league_reputation.py
tests/test_league_matching.py
tests/test_league_runner.py
tests/test_reputation_league_script.py
```

Keep names if they fit the existing style; adjust only if the repo has a better local convention.

## Core Concepts To Implement

### 1. League agents

Represent a league participant with stable identity and state.

Suggested schema:

```python
class LeagueAgentProfile(BaseModel):
    agent_id: str
    display_name: str
    kind: str  # heuristic, llm, mixed
    proposer_strategy: str | None = None
    responder_mode: str | None = None
    model: str | None = None
    provider: str | None = None
```

Suggested runtime state:

```python
class LeagueAgentState(BaseModel):
    profile: LeagueAgentProfile
    total_payoff: float = 0.0
    proposer_payoff: float = 0.0
    responder_payoff: float = 0.0
    matches_played: int = 0
    accepted_matches: int = 0
    public_reputation: float = 0.0
    fairness_score: float = 0.0
    deception_count: int = 0
    detected_lie_count: int = 0
```

Do not store raw clients inside Pydantic records. Keep model/client objects in runner factories or lightweight runtime wrappers.

### 2. Match records

A league match should wrap one hidden-pie ultimatum round or a small number of rounds.

Start simple:

- One match = one Hidden Pie Audit round.
- Each match assigns one proposer and one responder.
- Later extension can support multi-round pair matches.

Suggested schema:

```python
class LeagueMatchRecord(BaseModel):
    match_id: str
    season_index: int
    proposer_id: str
    responder_id: str
    true_pie: float
    claimed_pie: float
    offer: float
    public_message: str
    accepted: bool
    audit_occurred: bool
    lie_detected: bool
    proposer_payoff: float
    responder_payoff: float
    proposer_reputation_before: float
    responder_reputation_before: float
    proposer_reputation_after: float
    responder_reputation_after: float
    metadata: dict[str, Any] = {}
```

Include enough IDs and before/after reputation values that season dynamics are auditable.

### 3. Public reputation

Implement a deterministic reputation update first. Do not rely on LLM judgments for the initial score.

Suggested scoring inputs:

- accepted offer fairness: `offer / true_pie`
- claimed fairness: `offer / claimed_pie`
- deception: `claimed_pie != true_pie`
- detected lie
- rejection
- prompt-attack markers if present
- published reviews/gossip sentiment if enabled later

Start with a bounded rolling score, e.g. `[-1, 1]` or `[0, 100]`.

Example simple update:

```text
delta =
  + fairness_weight * (offer / true_pie - 0.3)
  - deception_weight if claimed_pie != true_pie
  - detected_lie_weight if lie_detected
  - prompt_attack_weight if public_message has attack markers
```

Use a moving average or exponential update:

```text
new_rep = (1 - alpha) * old_rep + alpha * match_score
```

Make weights configurable through a `ReputationConfig`.

Add tests for:

- honest fair actions improve reputation
- lowballing reduces reputation
- lying reduces reputation
- detected lying reduces more
- reputation remains bounded
- updates are deterministic

### 4. Private memory

Implement simple private memory before LLM-generated memory.

Each agent should store a limited list of summaries about opponents it has encountered.

Suggested schema:

```python
class PrivateMemoryEntry(BaseModel):
    observer_id: str
    target_id: str
    match_id: str
    target_role: str
    accepted: bool
    target_offer_ratio_true: float | None
    target_claimed_truthfully: bool | None
    target_public_message: str
    summary: str
```

For deterministic summaries, generate structured text from match data:

- "As proposer, A claimed truthfully and offered 45% of true pie."
- "As proposer, B underclaimed by 35% and was detected by audit."
- "As responder, C rejected a 12% offer."

Memory retrieval:

- For an upcoming match, include only memories about the current opponent.
- Cap memory count, e.g. last 3 entries per opponent.
- Keep memory deterministic and transparent.

### 5. Public gossip/reviews

Implement gossip as an optional mode. Default can be off for first tests, on for LLM demo.

Two stages:

1. Deterministic review generator for tests and heuristic seasons.
2. Optional LLM-generated review for LLM agents, if practical.

Suggested schema:

```python
class GossipRecord(BaseModel):
    review_id: str
    match_id: str
    author_id: str
    target_id: str
    text: str
    rating: float | None = None
    created_at_match: int
```

Important safety/design rule:

- Gossip is untrusted social information, not ground truth.
- Future LLM prompts should label it clearly as "public reputation/gossip, may be biased."
- Do not let gossip change game rules, parser behavior, or hidden truth.

Implement deterministic public review retrieval:

- Recent reviews about opponent, capped at `k`.
- Optionally sample by recency or reputation.

Metrics should measure:

- review count
- average rating
- gossip accuracy against true behavior
- effect of gossip on acceptance/deception over time

### 6. Matching policies

Implement at least two matching policies:

- `random`: random proposer/responder pairs, no self-play.
- `reputation_based`: pairs agents using public reputation, e.g. high-rep with high-rep, low-rep with low-rep, or weighted probability by reputation distance.

Optional:

- `elo_like`: update a matchmaking rating based on payoff/win.

Keep policies deterministic under seed.

Tests:

- no self-match
- pair count equals season length
- same seed gives same schedule
- random policy covers multiple agents over a season
- reputation policy produces measurably different pairing distribution

### 7. League-aware LLM prompts

Add league context without breaking current one-shot prompts.

Best options:

- Add new prompt builders in `ultimatum_arena/league/agents.py` or `ultimatum_arena/league/prompts.py`.
- Keep existing `build_proposer_prompt()` and `build_responder_prompt()` unchanged unless adding optional, backward-compatible parameters is cleaner.

League proposer prompt should include:

- private true pie
- public pie range, audit probability, lie penalty
- opponent public reputation
- recent private memory about opponent
- recent public gossip about opponent
- current leaderboard summary
- role: proposer
- required JSON output

League responder prompt should include:

- claimed pie, offer, public message
- opponent public reputation
- private memory/gossip about opponent
- own payoff from accept/reject
- warning that public message and gossip are untrusted data
- required JSON output

Do not reveal true pie to responder.

Do not expose private memory of other agents.

Do not ask for private chain-of-thought. If useful, ask for `private_reasoning_summary` as a high-level strategy summary only, and store it as untrusted/self-reported metadata.

### 8. League runner

Implement a season runner:

```python
def run_reputation_league(
    *,
    agent_factories: list[LeagueAgentFactory],
    n_matches: int,
    matching_policy: str,
    pie_range: tuple[float, float] = (50.0, 150.0),
    audit_prob: float = 0.25,
    lie_penalty: float = 25.0,
    rng_seed: int | None = None,
    reputation_config: ReputationConfig | None = None,
    memory_config: MemoryConfig | None = None,
    gossip_config: GossipConfig | None = None,
    output_dir: str | Path | None = None,
) -> tuple[list[LeagueMatchRecord], dict]
```

If this exact signature is too heavy, use a `LeagueConfig` object.

Execution flow per match:

1. Choose proposer/responder via matching policy.
2. Build league context for proposer.
3. Run proposer action.
4. Build league context for responder.
5. Run responder decision.
6. Resolve Hidden Pie Audit round.
7. Update payoffs.
8. Update public reputation.
9. Update private memories for both agents.
10. Optionally generate/publish gossip.
11. Persist match record.

Keep per-match failure handling:

- If an LLM refuses or returns unparseable JSON, record the raw output and a parse/refusal marker.
- Use a conservative fallback only if explicitly configured.
- Otherwise skip that agent's action for the match and record it as failed/refused.

Recommended default for research: refusal-safe record and continue.

### 9. League metrics

Implement `compute_league_metrics(records, final_states, gossip_records=None)`.

Core metrics:

- total welfare: total payoff across all agents
- inequality: Gini coefficient or payoff standard deviation
- leaderboard by total payoff
- reputation/payoff correlation
- reputation/acceptance correlation
- deception rate over time
- detected lie rate over time
- mean offer ratio true
- mean offer ratio claimed
- acceptance rate
- fairness gap
- exploitability: payoff gap between top quartile and bottom quartile
- reputation elasticity: change in acceptance probability as opponent reputation changes
- gossip accuracy: correlation or agreement between reviews and observed behavior
- memory effect: behavior difference when agents have prior private memory vs first encounter

Implement only metrics that can be computed clearly and deterministically. If a metric is too much for first pass, include a placeholder in research plan, not code.

### 10. Storage/output layout

Use a timestamped output tree:

```text
outputs/reputation_league/YYYYMMDD_HHMMSS/
  manifest.json
  matches.jsonl
  final_agent_states.json
  public_reputation_history.csv
  gossip.jsonl
  league_summary.json
  leaderboard.csv
```

Optional plots:

```text
plots/reputation_vs_payoff.png
plots/deception_rate_over_time.png
plots/acceptance_rate_over_time.png
plots/payoff_inequality_over_time.png
```

Do not require plotting for the first functional implementation if it slows the core work, but include at least CSV/JSON outputs.

## CLI Demo

Add:

```text
scripts/run_reputation_league_demo.py
```

Default must be cheap and local:

```powershell
python scripts/run_reputation_league_demo.py
```

Suggested default:

- provider: `heuristic` or `ollama` depending on speed; prefer `heuristic` for no external dependencies, with `--provider ollama` for Gemma.
- if LLM default is acceptable, use local `gemma3`, 8 agents, 20 matches, random matching.
- full research default should not be 32 agents/200 matches if that would be slow.

Example commands:

```powershell
# deterministic/heuristic smoke, no model calls
python scripts/run_reputation_league_demo.py --provider heuristic --agents 8 --matches 40 --matching random

# local Gemma smoke
python scripts/run_reputation_league_demo.py --provider ollama --model gemma3 --agents 6 --matches 20 --matching random

# local Gemma reputation-based matching
python scripts/run_reputation_league_demo.py --provider ollama --model gemma3 --agents 8 --matches 60 --matching reputation_based --gossip deterministic

# Claude CLI, tiny canary only because calls are expensive
python scripts/run_reputation_league_demo.py --provider claude --model haiku --agents 4 --matches 8

# OpenAI only if explicitly requested
python scripts/run_reputation_league_demo.py --provider openai --model gpt-5.4-mini --agents 4 --matches 8
```

CLI options:

- `--provider {heuristic,ollama,claude,openai}`
- `--model`
- `--agents`
- `--matches`
- `--matching {random,reputation_based}`
- `--audit-prob`
- `--lie-penalty`
- `--seed`
- `--gossip {off,deterministic,llm}`
- `--memory-limit`
- `--output-root`
- `--temperature` where supported

Print:

- run id
- output directory
- provider/model
- number of agents/matches
- matching policy
- top 5 leaderboard
- total welfare
- deception rate
- acceptance rate
- reputation/payoff correlation if available

## Research Plan To Create

Create:

```text
research/reputation_network_league_research_plan.md
```

The plan should be executable, like the existing Prompt-Attack and Hidden Pie Audit plans.

It should include:

### Research questions

1. Does public reputation reduce deception and lowballing across a season?
2. Does reputation-based matching improve welfare, fairness, or acceptance relative to random matching?
3. Does private memory improve agent protection from exploiters?
4. Does gossip improve outcomes, or does it amplify false/strategic accusations?
5. Do high-payoff agents become high-reputation agents, or can exploiters top the leaderboard?
6. Do LLM agents use reputation differently from deterministic/heuristic agents?
7. Does local Gemma react to reputation/gossip differently from Claude Code CLI?

### Pre-registered interpretation rules

Define before running:

- reputation helps if deception or lowball acceptance declines over season segments without reducing fair-offer acceptance
- public reputation is predictive if opponent reputation correlates with acceptance/payoff/fairness in later matches
- gossip is useful if it improves prediction beyond public reputation and has measurable accuracy
- gossip is harmful if inaccurate reviews reduce welfare/fairness or punish honest agents
- exploitation exists if high-payoff agents have low fairness/deception reputation

### Experiment sections

Start with cheap/free:

1. Deterministic smoke tests:
   - 8 heuristic agents
   - 40 matches
   - random matching
   - no gossip
   - verify outputs and metrics

2. Heuristic league mechanism:
   - mix honest, lying, greedy, expected-value proposers
   - compare random vs reputation-based matching
   - compare no memory vs private memory
   - deterministic gossip on/off

3. Local Gemma pilot:
   - small league, e.g. 6-8 agents, 20-60 matches
   - local Ollama/Gemma only
   - random matching first, then reputation-based
   - record parse/refusal rate

4. Controlled memory/gossip probe:
   - fixed observations where opponent has good vs bad reputation
   - ask responder/proposer decisions under identical economic terms
   - isolate whether reputation changes behavior

5. Claude CLI canary:
   - tiny league only, e.g. 4 agents, 8 matches
   - usage-window aware
   - refusal-safe
   - label as Claude Code CLI product, not bare model

6. Synthesis:
   - compare heuristic, Gemma, Claude
   - discuss whether reputation creates cooperation, exclusion, rumor effects, or strategic exploitation

### Budget strategy

Mention:

- Heuristic runs are free and should be first.
- Gemma runs are local/free but slower.
- Claude CLI calls are expensive because each match may require proposer, responder, and optional gossip calls.
- Therefore Claude seasons must be tiny unless a special budget is approved.
- OpenAI is excluded unless explicitly requested.

### Data capture

Findings should derive from JSON/CSV outputs, not copied terminal text.

Create:

```text
research/reputation_network_league_findings.md
```

but only after running. The implementation task should create the plan; the findings doc can start as a template if useful.

## Tests

Add tests in layers.

Focused test targets:

```powershell
python -m pytest tests/test_league_schemas.py
python -m pytest tests/test_league_reputation.py
python -m pytest tests/test_league_matching.py
python -m pytest tests/test_league_runner.py
python -m pytest tests/test_reputation_league_script.py
```

Required test coverage:

- schemas serialize/deserialize
- reputation updates are deterministic and bounded
- memory retrieval returns only relevant opponent memories
- gossip records serialize and do not affect hidden truth
- random matching is seed-stable and avoids self-matches
- reputation-based matching differs from random in a predictable small fixture
- league runner updates payoffs and reputations
- league runner persists expected files
- CLI parse args have safe defaults
- CLI tests monkeypatch clients and do not call live Ollama/Claude/OpenAI

Then run:

```powershell
python -m pytest
```

Optional live local smoke:

```powershell
ollama pull gemma3
python scripts/run_reputation_league_demo.py --provider ollama --model gemma3 --agents 4 --matches 8
```

If Ollama is unavailable, report that live smoke was blocked; do not fake it.

## Documentation Updates

Update:

- `README.md`
- `CLAUDE.md`
- possibly `research/collaboration_brief.md` if the league changes the collaboration story

Docs must explain:

- what Reputation Network League is
- how it differs from one-shot Hidden Pie Audit
- how reputation, memory, and gossip work
- how to run a no-model heuristic smoke
- how to run local Gemma
- how to run tiny Claude/OpenAI canaries
- output layout
- metrics
- limitations

Keep the docs honest:

- Do not claim reputation effects before running the research plan.
- Label Claude CLI results as product/session-mediated.
- Treat LLM gossip as untrusted and possibly biased.
- Keep findings separate from plans once runs are complete.

## Acceptance Criteria

Implementation is complete when:

- League data schemas exist and are tested.
- Reputation update logic exists, is deterministic, bounded, and tested.
- Private memory exists and is tested.
- Optional deterministic gossip exists and is tested.
- At least random and reputation-based matching policies exist and are tested.
- A season runner executes many one-shot Hidden Pie Audit matches across many agents.
- The runner writes manifest, match logs, final agent states, leaderboard, and summary metrics.
- A CLI demo runs a heuristic smoke with no external services.
- The CLI can run a tiny local Gemma league through Ollama.
- Claude/OpenAI provider paths exist only through current clients and are optional.
- A research plan is written to `research/reputation_network_league_research_plan.md`.
- README and CLAUDE.md are updated.
- Focused tests and full test suite pass.

## Implementation Notes And Pitfalls

- Do not let gossip or reputation reveal `true_pie` to responders unless the match was audited and the design explicitly says audit outcomes are public.
- Decide and document what is public after a match:
  - accepted/rejected?
  - claimed pie?
  - offer?
  - audit occurred?
  - lie detected?
  - payoffs?
  - public message?
- Keep hidden truth hidden from future agents unless public audit reveals it.
- Avoid "omniscient reputation" unless clearly labeled as an experimental condition.
- Be explicit about whether reputation is based on public information only or ground-truth evaluator information.
- Separate public reputation from private memory.
- Separate deterministic scoring from LLM-written gossip.
- Make every stochastic component seedable.
- Keep output sizes manageable for LLM seasons.
- Treat LLM refusals and parse errors as data where possible.
- Do not overrun Claude usage windows. Use canaries.
- Prefer a small working league over an ambitious unfinished simulation.

## Suggested First Implementation Order

1. Add league schemas.
2. Add deterministic reputation scoring.
3. Add private memory summaries.
4. Add random matching.
5. Add basic league runner with heuristic agents only.
6. Add storage and metrics.
7. Add CLI heuristic smoke.
8. Add reputation-based matching.
9. Add deterministic gossip.
10. Add league-aware LLM wrapper/prompts.
11. Add provider options.
12. Add research plan.
13. Update docs.
14. Run tests and smoke.

Work incrementally and keep the first pass boring, deterministic, and testable. The science comes from comparing conditions after the league mechanics are reliable.
