"""LLM-backed proposer and responder agents."""

from __future__ import annotations

from ultimatum_arena.agents.base import BaseProposer, BaseResponder
from ultimatum_arena.llm.client import LLMClient
from ultimatum_arena.llm.errors import LLMParseError
from ultimatum_arena.llm.parser import parse_proposer_response, parse_responder_response
from ultimatum_arena.llm.prompts import (
    VALID_RESPONDER_PROMPT_MODES,
    VALID_STRATEGIES,
    build_proposer_prompt,
    build_responder_prompt,
)
from ultimatum_arena.schemas import (
    ProposerAction,
    ProposerObservation,
    ResponderAction,
    ResponderObservation,
)


class LLMProposer(BaseProposer):
    """Proposer agent that delegates decisions to an LLM.

    After each call to :meth:`act`, the following attributes are updated for
    observability:

    * ``last_prompt`` – the prompt string sent to the model.
    * ``last_raw_response`` – the raw text the model returned.
    * ``last_parse_error`` – error message string if parsing failed and a
      fallback was used, otherwise ``None``.

    Parameters
    ----------
    client:
        Any object satisfying the :class:`LLMClient` protocol.
    strategy:
        Behavioural profile injected into the proposer prompt.  One of
        ``"honest_fair"`` (default), ``"self_interested"``, or
        ``"deceptive"``.  Raises :class:`ValueError` for unknown values.
    """

    def __init__(self, client: LLMClient, strategy: str = "honest_fair") -> None:
        if strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Unknown strategy {strategy!r}. "
                f"Valid strategies: {sorted(VALID_STRATEGIES)}"
            )
        self._client = client
        self._strategy = strategy
        self.last_prompt: str = ""
        self.last_raw_response: str = ""
        self.last_parse_error: str | None = None

    @property
    def strategy(self) -> str:
        """The behavioural strategy profile for this proposer."""
        return self._strategy

    def act(self, obs: ProposerObservation) -> ProposerAction:
        prompt = build_proposer_prompt(obs, strategy=self._strategy)
        self.last_prompt = prompt
        self.last_parse_error = None
        text = self._client.generate(prompt)
        self.last_raw_response = text
        try:
            return parse_proposer_response(text, obs)
        except LLMParseError as exc:
            self.last_parse_error = str(exc)
            raise


class LLMResponder(BaseResponder):
    """Responder agent that delegates decisions to an LLM.

    After each call to :meth:`act`, the following attributes are updated for
    observability:

    * ``last_prompt`` – the prompt string sent to the model.
    * ``last_raw_response`` – the raw text the model returned.
    * ``last_parse_error`` – error message string if parsing failed and a
      fallback was used, otherwise ``None``.

    Parameters
    ----------
    client:
        Any object satisfying the :class:`LLMClient` protocol.
    prompt_mode:
        One of ``"standard"`` (default), ``"robust"``, or ``"naive"``.  Selects
        how the proposer's ``public_message`` is framed in the responder prompt.
        ``robust`` treats the message as untrusted data and instructs the model
        not to follow instructions embedded in it.  Raises :class:`ValueError`
        for unknown modes.
    """

    def __init__(self, client: LLMClient, prompt_mode: str = "standard") -> None:
        if prompt_mode not in VALID_RESPONDER_PROMPT_MODES:
            raise ValueError(
                f"Unknown responder prompt mode {prompt_mode!r}. "
                f"Valid modes: {sorted(VALID_RESPONDER_PROMPT_MODES)}"
            )
        self._client = client
        self._prompt_mode = prompt_mode
        self.last_prompt: str = ""
        self.last_raw_response: str = ""
        self.last_parse_error: str | None = None

    @property
    def prompt_mode(self) -> str:
        """The responder prompt mode (``"standard"``, ``"robust"``, or ``"naive"``)."""
        return self._prompt_mode

    def act(self, obs: ResponderObservation) -> ResponderAction:
        prompt = build_responder_prompt(obs, prompt_mode=self._prompt_mode)
        self.last_prompt = prompt
        self.last_parse_error = None
        text = self._client.generate(prompt)
        self.last_raw_response = text
        try:
            return parse_responder_response(text)
        except LLMParseError as exc:
            self.last_parse_error = str(exc)
            raise
