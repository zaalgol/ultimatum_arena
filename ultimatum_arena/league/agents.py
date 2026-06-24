"""Runtime participant wrappers for the league.

A :class:`LeagueParticipant` is the league's view of an agent: it carries the
stable :class:`LeagueAgentProfile` and knows how to act in either role given a
:class:`~ultimatum_arena.league.prompts.LeagueContext`.

Two concrete participants are provided:

* :class:`HeuristicParticipant` — wraps deterministic
  :class:`~ultimatum_arena.agents.base.BaseProposer` /
  :class:`~ultimatum_arena.agents.base.BaseResponder` instances. It ignores the
  league context (heuristics do not react to reputation/gossip), which makes it
  the perfect deterministic control.
* :class:`LLMParticipant` — drives an :class:`LLMClient` with league-aware
  prompts so the model can see opponent reputation, memory, and gossip.

Raw clients live here on runtime wrappers, never on the Pydantic records.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ultimatum_arena.agents.base import BaseProposer, BaseResponder
from ultimatum_arena.league.prompts import (
    LeagueContext,
    build_league_proposer_prompt,
    build_league_responder_prompt,
)
from ultimatum_arena.league.schemas import LeagueAgentProfile
from ultimatum_arena.llm.client import LLMClient
from ultimatum_arena.llm.parser import parse_proposer_response, parse_responder_response
from ultimatum_arena.llm.prompts import VALID_RESPONDER_PROMPT_MODES, VALID_STRATEGIES
from ultimatum_arena.schemas import (
    ProposerAction,
    ProposerObservation,
    ResponderAction,
    ResponderObservation,
)


class LeagueParticipant(ABC):
    """A league agent that can act as proposer or responder with social context."""

    def __init__(self, profile: LeagueAgentProfile) -> None:
        self.profile = profile
        # Observability, mirroring the LLM agents' attributes.
        self.last_prompt: str = ""
        self.last_raw_response: str = ""
        self.last_parse_error: str | None = None

    @property
    def agent_id(self) -> str:
        return self.profile.agent_id

    @abstractmethod
    def propose(self, obs: ProposerObservation, context: LeagueContext) -> ProposerAction:
        ...

    @abstractmethod
    def respond(self, obs: ResponderObservation, context: LeagueContext) -> ResponderAction:
        ...


class HeuristicParticipant(LeagueParticipant):
    """Wraps deterministic proposer/responder agents; ignores social context."""

    def __init__(
        self,
        profile: LeagueAgentProfile,
        proposer: BaseProposer,
        responder: BaseResponder,
    ) -> None:
        super().__init__(profile)
        self._proposer = proposer
        self._responder = responder

    def propose(self, obs: ProposerObservation, context: LeagueContext) -> ProposerAction:
        action = self._proposer.act(obs)
        self.last_raw_response = action.model_dump_json()
        return action

    def respond(self, obs: ResponderObservation, context: LeagueContext) -> ResponderAction:
        action = self._responder.act(obs)
        self.last_raw_response = action.model_dump_json()
        return action


class LLMParticipant(LeagueParticipant):
    """Drives an ``LLMClient`` with league-aware prompts in both roles."""

    def __init__(
        self,
        profile: LeagueAgentProfile,
        client: LLMClient,
        *,
        strategy: str = "honest_fair",
        responder_mode: str = "standard",
    ) -> None:
        if strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Unknown strategy {strategy!r}. Valid: {sorted(VALID_STRATEGIES)}"
            )
        if responder_mode not in VALID_RESPONDER_PROMPT_MODES:
            raise ValueError(
                f"Unknown responder mode {responder_mode!r}. "
                f"Valid: {sorted(VALID_RESPONDER_PROMPT_MODES)}"
            )
        super().__init__(profile)
        self._client = client
        self._strategy = strategy
        self._responder_mode = responder_mode

    @property
    def strategy(self) -> str:
        return self._strategy

    @property
    def responder_mode(self) -> str:
        return self._responder_mode

    def propose(self, obs: ProposerObservation, context: LeagueContext) -> ProposerAction:
        prompt = build_league_proposer_prompt(obs, self._strategy, context)
        self.last_prompt = prompt
        self.last_parse_error = None
        text = self._client.generate(prompt)
        self.last_raw_response = text
        try:
            return parse_proposer_response(text, obs)
        except Exception as exc:  # LLMParseError and any parse-time failure
            self.last_parse_error = str(exc)
            raise

    def respond(self, obs: ResponderObservation, context: LeagueContext) -> ResponderAction:
        prompt = build_league_responder_prompt(obs, self._responder_mode, context)
        self.last_prompt = prompt
        self.last_parse_error = None
        text = self._client.generate(prompt)
        self.last_raw_response = text
        try:
            return parse_responder_response(text)
        except Exception as exc:
            self.last_parse_error = str(exc)
            raise
