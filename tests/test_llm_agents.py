"""Tests for LLM infrastructure: FakeLLMClient, prompt builders, parser,
and LLMProposer / LLMResponder agents."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ultimatum_arena.llm.client import FakeLLMClient, LLMClient
from ultimatum_arena.llm.errors import LLMParseError
from ultimatum_arena.llm.parser import (
    extract_json,
    parse_proposer_response,
    parse_responder_response,
)
from ultimatum_arena.llm.prompts import VALID_STRATEGIES, build_proposer_prompt, build_responder_prompt
from ultimatum_arena.llm.agents import LLMProposer, LLMResponder
from ultimatum_arena.schemas import (
    ProposerObservation,
    ResponderObservation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _proposer_obs(true_pie: float = 100.0, round_index: int = 0) -> ProposerObservation:
    return ProposerObservation(
        true_pie=true_pie,
        pie_range=(50.0, 150.0),
        round_index=round_index,
    )


def _responder_obs(
    claimed_pie: float = 100.0,
    offer: float = 40.0,
    round_index: int = 0,
    public_message: str = "",
) -> ResponderObservation:
    return ResponderObservation(
        claimed_pie=claimed_pie,
        offer=offer,
        public_message=public_message,
        pie_range=(50.0, 150.0),
        round_index=round_index,
    )


# ---------------------------------------------------------------------------
# Public import surface
# ---------------------------------------------------------------------------

class TestPublicImports:
    def test_llm_proposer_importable_from_agents(self):
        from ultimatum_arena.agents import LLMProposer  # noqa: F401

    def test_llm_responder_importable_from_agents(self):
        from ultimatum_arena.agents import LLMResponder  # noqa: F401


# ---------------------------------------------------------------------------
# FakeLLMClient
# ---------------------------------------------------------------------------

class TestFakeLLMClient:
    def test_satisfies_protocol(self):
        client = FakeLLMClient()
        assert isinstance(client, LLMClient)

    def test_returns_default_response(self):
        client = FakeLLMClient()
        result = client.generate("anything")
        assert '"claimed_pie"' in result

    def test_records_calls(self):
        client = FakeLLMClient(responses=["resp1", "resp2"])
        client.generate("p1")
        client.generate("p2")
        assert client.calls == ["p1", "p2"]

    def test_cycles_through_responses(self):
        client = FakeLLMClient(responses=["a", "b"])
        results = [client.generate("x") for _ in range(5)]
        assert results == ["a", "b", "a", "b", "a"]

    def test_single_response_repeated(self):
        client = FakeLLMClient(responses=["only"])
        assert client.generate("x") == "only"
        assert client.generate("y") == "only"

    def test_empty_calls_initially(self):
        client = FakeLLMClient()
        assert client.calls == []


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

class TestBuildProposerPrompt:
    def test_contains_true_pie(self):
        obs = _proposer_obs(true_pie=123.45)
        prompt = build_proposer_prompt(obs)
        assert "123.45" in prompt

    def test_contains_pie_range(self):
        obs = _proposer_obs()
        prompt = build_proposer_prompt(obs)
        assert "50.00" in prompt
        assert "150.00" in prompt

    def test_contains_round_number(self):
        obs = _proposer_obs(round_index=4)
        prompt = build_proposer_prompt(obs)
        assert "5" in prompt  # round_index + 1

    def test_contains_json_instruction(self):
        prompt = build_proposer_prompt(_proposer_obs())
        assert "claimed_pie" in prompt
        assert "offer" in prompt

    def test_does_not_mention_role_responder(self):
        prompt = build_proposer_prompt(_proposer_obs())
        assert "PROPOSER" in prompt


class TestResponderPromptPayoffWording:
    def test_does_not_claim_proposer_earns_claimed_pie_minus_offer(self):
        obs = _responder_obs(claimed_pie=80.0, offer=30.0)
        prompt = build_responder_prompt(obs)
        # Must not state the incorrect formula "claimed_pie - offer" or "claimed_pie − offer"
        assert "claimed_pie - offer" not in prompt
        assert "claimed_pie \u2212 offer" not in prompt
        assert "(claimed_pie" not in prompt

    def test_does_not_reveal_true_pie_value(self):
        obs = _responder_obs(claimed_pie=80.0, offer=30.0)
        prompt = build_responder_prompt(obs)
        assert "true_pie" not in prompt.lower()

    def test_mentions_cannot_observe_true_pie(self):
        obs = _responder_obs()
        prompt = build_responder_prompt(obs)
        assert "cannot observe" in prompt.lower() or "true pie" in prompt.lower()


class TestBuildResponderPrompt:
    def test_contains_claimed_pie(self):
        obs = _responder_obs(claimed_pie=80.0)
        prompt = build_responder_prompt(obs)
        assert "80.00" in prompt

    def test_contains_offer(self):
        obs = _responder_obs(offer=35.0)
        prompt = build_responder_prompt(obs)
        assert "35.00" in prompt

    def test_contains_pie_range(self):
        obs = _responder_obs()
        prompt = build_responder_prompt(obs)
        assert "50.00" in prompt
        assert "150.00" in prompt

    def test_message_line_present_when_set(self):
        obs = _responder_obs(public_message="trust me")
        prompt = build_responder_prompt(obs)
        assert "trust me" in prompt

    def test_message_line_absent_when_empty(self):
        obs = _responder_obs(public_message="")
        prompt = build_responder_prompt(obs)
        assert "Proposer's message" not in prompt

    def test_contains_round_number(self):
        obs = _responder_obs(round_index=2)
        prompt = build_responder_prompt(obs)
        assert "3" in prompt  # round_index + 1


# ---------------------------------------------------------------------------
# extract_json
# ---------------------------------------------------------------------------

class TestExtractJson:
    def test_direct_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_json_with_whitespace(self):
        assert extract_json('  {"a": 1}  ') == {"a": 1}

    def test_code_fence_json(self):
        text = '```json\n{"a": 1}\n```'
        assert extract_json(text) == {"a": 1}

    def test_code_fence_no_lang(self):
        text = '```\n{"a": 1}\n```'
        assert extract_json(text) == {"a": 1}

    def test_json_with_preamble(self):
        text = 'Here is my response: {"a": 1} done.'
        assert extract_json(text) == {"a": 1}

    def test_nested_json(self):
        text = '{"outer": {"inner": 42}}'
        result = extract_json(text)
        assert result["outer"]["inner"] == 42

    def test_raises_on_no_json(self):
        with pytest.raises(LLMParseError):
            extract_json("no json here")

    def test_raises_on_empty(self):
        with pytest.raises(LLMParseError):
            extract_json("")

    def test_raises_on_malformed(self):
        with pytest.raises(LLMParseError):
            extract_json("{bad json}")


# ---------------------------------------------------------------------------
# parse_proposer_response
# ---------------------------------------------------------------------------

class TestParseProposerResponse:
    def test_valid_response(self):
        obs = _proposer_obs(true_pie=100.0)
        text = '{"claimed_pie": 90.0, "offer": 30.0, "public_message": "hello"}'
        action = parse_proposer_response(text, obs)
        assert action.claimed_pie == 90.0
        assert action.offer == 30.0
        assert action.public_message == "hello"

    def test_missing_claimed_pie_falls_back_to_true_pie(self):
        obs = _proposer_obs(true_pie=100.0)
        text = '{"offer": 40.0}'
        action = parse_proposer_response(text, obs)
        assert action.claimed_pie == 100.0

    def test_offer_clamped_to_claimed_pie(self):
        obs = _proposer_obs(true_pie=100.0)
        text = '{"claimed_pie": 80.0, "offer": 999.0}'
        action = parse_proposer_response(text, obs)
        assert action.offer == 80.0

    def test_negative_offer_clamped_to_zero(self):
        obs = _proposer_obs(true_pie=100.0)
        text = '{"claimed_pie": 80.0, "offer": -5.0}'
        action = parse_proposer_response(text, obs)
        assert action.offer == 0.0

    def test_zero_or_negative_claimed_pie_falls_back(self):
        obs = _proposer_obs(true_pie=100.0)
        text = '{"claimed_pie": -10.0, "offer": 5.0}'
        action = parse_proposer_response(text, obs)
        assert action.claimed_pie == 100.0

    def test_missing_offer_defaults_to_half_claimed(self):
        obs = _proposer_obs(true_pie=100.0)
        text = '{"claimed_pie": 80.0}'
        action = parse_proposer_response(text, obs)
        assert action.offer == 40.0

    def test_empty_public_message(self):
        obs = _proposer_obs()
        text = '{"claimed_pie": 100.0, "offer": 50.0}'
        action = parse_proposer_response(text, obs)
        assert action.public_message == ""

    def test_raises_on_unparseable(self):
        obs = _proposer_obs()
        with pytest.raises(LLMParseError):
            parse_proposer_response("not json at all", obs)


# ---------------------------------------------------------------------------
# parse_responder_response
# ---------------------------------------------------------------------------

class TestParseResponderResponse:
    def test_bool_true(self):
        assert parse_responder_response('{"accept": true}').accept is True

    def test_bool_false(self):
        assert parse_responder_response('{"accept": false}').accept is False

    def test_string_yes(self):
        assert parse_responder_response('{"accept": "yes"}').accept is True

    def test_string_no(self):
        assert parse_responder_response('{"accept": "no"}').accept is False

    def test_string_true(self):
        assert parse_responder_response('{"accept": "true"}').accept is True

    def test_string_false(self):
        assert parse_responder_response('{"accept": "false"}').accept is False

    def test_string_accept(self):
        assert parse_responder_response('{"accept": "accept"}').accept is True

    def test_int_1(self):
        assert parse_responder_response('{"accept": 1}').accept is True

    def test_int_0(self):
        assert parse_responder_response('{"accept": 0}').accept is False

    def test_missing_key_defaults_false(self):
        assert parse_responder_response('{"other": "stuff"}').accept is False

    def test_raises_on_unparseable(self):
        with pytest.raises(LLMParseError):
            parse_responder_response("no json")


# ---------------------------------------------------------------------------
# LLMProposer and LLMResponder integration with FakeLLMClient
# ---------------------------------------------------------------------------

class TestLLMProposer:
    def test_act_returns_proposer_action(self):
        client = FakeLLMClient(
            responses=['{"claimed_pie": 90.0, "offer": 35.0, "public_message": "hi"}']
        )
        proposer = LLMProposer(client)
        action = proposer.act(_proposer_obs(true_pie=100.0))
        assert action.claimed_pie == 90.0
        assert action.offer == 35.0
        assert action.public_message == "hi"

    def test_prompt_is_sent_to_client(self):
        client = FakeLLMClient()
        LLMProposer(client).act(_proposer_obs())
        assert len(client.calls) == 1
        assert "true_pie" in client.calls[0].lower() or "100" in client.calls[0]

    def test_fallback_on_partial_response(self):
        # Only offer provided — claimed_pie falls back to true_pie
        client = FakeLLMClient(responses=['{"offer": 20.0}'])
        action = LLMProposer(client).act(_proposer_obs(true_pie=100.0))
        assert action.claimed_pie == 100.0
        assert action.offer == 20.0


class TestLLMResponder:
    def test_act_accept_true(self):
        client = FakeLLMClient(responses=['{"accept": true}'])
        action = LLMResponder(client).act(_responder_obs())
        assert action.accept is True

    def test_act_accept_false(self):
        client = FakeLLMClient(responses=['{"accept": false}'])
        action = LLMResponder(client).act(_responder_obs())
        assert action.accept is False

    def test_prompt_is_sent_to_client(self):
        client = FakeLLMClient(responses=['{"accept": true}'])
        LLMResponder(client).act(_responder_obs(claimed_pie=80.0, offer=30.0))
        assert len(client.calls) == 1
        assert "80" in client.calls[0]

    def test_missing_accept_key_defaults_false(self):
        client = FakeLLMClient(responses=['{"reasoning": "too low"}'])
        action = LLMResponder(client).act(_responder_obs())
        assert action.accept is False


# ---------------------------------------------------------------------------
# Task A: LLM agent observability attributes
# ---------------------------------------------------------------------------

class TestLLMProposerObservability:
    def test_last_raw_response_set_after_act(self):
        raw = '{"claimed_pie": 90.0, "offer": 40.0, "public_message": ""}'
        client = FakeLLMClient(responses=[raw])
        proposer = LLMProposer(client)
        proposer.act(_proposer_obs())
        assert proposer.last_raw_response == raw

    def test_last_prompt_set_after_act(self):
        client = FakeLLMClient()
        proposer = LLMProposer(client)
        proposer.act(_proposer_obs(true_pie=75.0))
        assert "75" in proposer.last_prompt

    def test_last_parse_error_none_on_success(self):
        client = FakeLLMClient()
        proposer = LLMProposer(client)
        proposer.act(_proposer_obs())
        assert proposer.last_parse_error is None

    def test_last_parse_error_set_on_bad_json(self):
        client = FakeLLMClient(responses=["not json at all!!!!"])
        proposer = LLMProposer(client)
        with pytest.raises(LLMParseError):
            proposer.act(_proposer_obs())
        assert proposer.last_parse_error is not None

    def test_initial_attributes_are_empty(self):
        proposer = LLMProposer(FakeLLMClient())
        assert proposer.last_prompt == ""
        assert proposer.last_raw_response == ""
        assert proposer.last_parse_error is None


class TestLLMResponderObservability:
    def test_last_raw_response_set_after_act(self):
        raw = '{"accept": true}'
        client = FakeLLMClient(responses=[raw])
        responder = LLMResponder(client)
        responder.act(_responder_obs())
        assert responder.last_raw_response == raw

    def test_last_prompt_set_after_act(self):
        client = FakeLLMClient(responses=['{"accept": true}'])
        responder = LLMResponder(client)
        responder.act(_responder_obs(claimed_pie=120.0, offer=55.0))
        assert "120" in responder.last_prompt

    def test_last_parse_error_none_on_success(self):
        client = FakeLLMClient(responses=['{"accept": true}'])
        responder = LLMResponder(client)
        responder.act(_responder_obs())
        assert responder.last_parse_error is None

    def test_last_parse_error_set_on_bad_json(self):
        client = FakeLLMClient(responses=["totally not json!!!!"])
        responder = LLMResponder(client)
        with pytest.raises(LLMParseError):
            responder.act(_responder_obs())
        assert responder.last_parse_error is not None

    def test_initial_attributes_are_empty(self):
        responder = LLMResponder(FakeLLMClient())
        assert responder.last_prompt == ""
        assert responder.last_raw_response == ""
        assert responder.last_parse_error is None


# ---------------------------------------------------------------------------
# Task A: run_experiment includes LLM metadata in results
# ---------------------------------------------------------------------------

class TestRunExperimentLLMMetadata:
    def _make_env(self):
        from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
        return HiddenPieAuditEnv(rng_seed=1)

    def test_llm_results_have_metadata(self):
        from ultimatum_arena.runners.basic import run_experiment
        proposer_client = FakeLLMClient(
            responses=['{"claimed_pie": 90.0, "offer": 40.0, "public_message": ""}']
        )
        responder_client = FakeLLMClient(responses=['{"accept": true}'])
        results, _ = run_experiment(
            LLMProposer(proposer_client),
            LLMResponder(responder_client),
            self._make_env(),
            n_rounds=2,
        )
        for r in results:
            assert "proposer_raw_response" in r.metadata
            assert "responder_raw_response" in r.metadata
            assert "proposer_prompt" in r.metadata
            assert "responder_prompt" in r.metadata

    def test_llm_metadata_contains_actual_response_text(self):
        from ultimatum_arena.runners.basic import run_experiment
        raw_proposer = '{"claimed_pie": 90.0, "offer": 40.0, "public_message": ""}'
        raw_responder = '{"accept": false}'
        results, _ = run_experiment(
            LLMProposer(FakeLLMClient(responses=[raw_proposer])),
            LLMResponder(FakeLLMClient(responses=[raw_responder])),
            self._make_env(),
            n_rounds=1,
        )
        assert results[0].metadata["proposer_raw_response"] == raw_proposer
        assert results[0].metadata["responder_raw_response"] == raw_responder

    def test_llm_metadata_in_jsonl(self):
        from ultimatum_arena.runners.basic import run_experiment
        from ultimatum_arena.storage.jsonl import load_results
        with tempfile.TemporaryDirectory() as tmpdir:
            run_experiment(
                LLMProposer(FakeLLMClient()),
                LLMResponder(FakeLLMClient(responses=['{"accept": true}'])),
                self._make_env(),
                n_rounds=3,
                output_dir=tmpdir,
                experiment_name="llm_meta_test",
            )
            jsonl_path = Path(tmpdir) / "llm_meta_test.jsonl"
            loaded = load_results(jsonl_path)
            assert len(loaded) == 3
            for r in loaded:
                assert "proposer_raw_response" in r.metadata
                assert "responder_raw_response" in r.metadata

    def test_heuristic_results_have_empty_metadata(self):
        from ultimatum_arena.runners.basic import run_experiment
        from ultimatum_arena.agents import HonestFairProposer, ThresholdResponder
        results, _ = run_experiment(
            HonestFairProposer(),
            ThresholdResponder(),
            self._make_env(),
            n_rounds=5,
        )
        for r in results:
            assert r.metadata == {}


# ---------------------------------------------------------------------------
# Task B: Prompt content assertions
# ---------------------------------------------------------------------------

class TestProposerPromptContent:
    def test_true_pie_is_prominent(self):
        obs = _proposer_obs(true_pie=83.5)
        prompt = build_proposer_prompt(obs)
        assert "83.5" in prompt or "83.50" in prompt

    def test_mentions_true_pie_is_private(self):
        prompt = build_proposer_prompt(_proposer_obs())
        lower = prompt.lower()
        assert "private" in lower or "only you" in lower or "only to you" in lower

    def test_mentions_responder_cannot_see_true_pie(self):
        prompt = build_proposer_prompt(_proposer_obs())
        lower = prompt.lower()
        assert "responder" in lower
        # The prompt should mention that responder does NOT see the true pie
        assert "not" in lower or "cannot" in lower or "hidden" in lower

    def test_mentions_audit_info(self):
        prompt = build_proposer_prompt(_proposer_obs())
        lower = prompt.lower()
        assert "audit" in lower

    def test_mentions_lie_penalty(self):
        prompt = build_proposer_prompt(_proposer_obs())
        lower = prompt.lower()
        assert "penalty" in lower or "penalt" in lower

    def test_json_only_instruction(self):
        prompt = build_proposer_prompt(_proposer_obs())
        lower = prompt.lower()
        assert "json" in lower
        assert "claimed_pie" in prompt

    def test_warns_against_default_values(self):
        prompt = build_proposer_prompt(_proposer_obs())
        lower = prompt.lower()
        assert "do not" in lower or "don't" in lower or "not 100" in lower or "actual" in lower

    def test_payoff_based_on_true_pie(self):
        prompt = build_proposer_prompt(_proposer_obs())
        lower = prompt.lower()
        assert "true pie" in lower or "true_pie" in lower


class TestResponderPromptContent:
    def test_offer_percentage_shown(self):
        obs = _responder_obs(claimed_pie=100.0, offer=40.0)
        prompt = build_responder_prompt(obs)
        # 40% of 100
        assert "40" in prompt

    def test_mentions_true_pie_hidden(self):
        obs = _responder_obs()
        prompt = build_responder_prompt(obs)
        lower = prompt.lower()
        assert "hidden" in lower or "cannot" in lower or "cannot observe" in lower

    def test_explains_reject_means_zero(self):
        obs = _responder_obs()
        prompt = build_responder_prompt(obs)
        lower = prompt.lower()
        assert "0" in prompt or "zero" in lower or "nothing" in lower or "both earn" in lower

    def test_guides_toward_rational_acceptance(self):
        obs = _responder_obs()
        prompt = build_responder_prompt(obs)
        lower = prompt.lower()
        assert "accept" in lower
        # Should mention some threshold or guidance for accepting
        assert (
            "rational" in lower or "25" in lower or "reasonable" in lower
            or "meaningful" in lower or "usually accept" in lower
        )

    def test_json_only_instruction(self):
        prompt = build_responder_prompt(_responder_obs())
        assert "json" in prompt.lower()
        assert '"accept"' in prompt or "accept" in prompt

    def test_operational_acceptance_threshold_25_pct(self):
        """Prompt must mention a 25% threshold so Gemma has a concrete rule."""
        obs = _responder_obs(claimed_pie=100.0, offer=40.0)
        prompt = build_responder_prompt(obs)
        assert "25%" in prompt or "25 %" in prompt

    def test_operational_acceptance_threshold_50_pct(self):
        """Prompt must strongly recommend acceptance at 50% or above."""
        obs = _responder_obs(claimed_pie=100.0, offer=40.0)
        prompt = build_responder_prompt(obs)
        assert "50%" in prompt or "50 %" in prompt
        assert "50% of the claimed pie, accept" in prompt

    def test_accept_gives_immediate_amount(self):
        """Prompt must state accepting gives the offer amount immediately."""
        obs = _responder_obs(claimed_pie=100.0, offer=40.0)
        prompt = build_responder_prompt(obs)
        # "Accepting gives you 40.00 immediately"
        assert "40.00" in prompt
        lower = prompt.lower()
        assert "immediately" in lower or "gives you" in lower

    def test_reject_gives_zero(self):
        """Prompt must state that rejecting gives exactly 0."""
        obs = _responder_obs()
        prompt = build_responder_prompt(obs)
        lower = prompt.lower()
        assert "0" in prompt
        assert "reject" in lower

    def test_audit_does_not_pay_responder(self):
        """Prompt must not imply audits give the responder compensation."""
        prompt = build_responder_prompt(_responder_obs())
        lower = prompt.lower()
        assert "audit" in lower
        assert "never gives you extra payoff" in lower

    def test_rejection_is_not_punishment_mechanism(self):
        """Prompt must discourage rejecting generous offers as punishment."""
        prompt = build_responder_prompt(_responder_obs())
        lower = prompt.lower()
        assert "rejecting is not a punishment mechanism" in lower

    def test_responder_goal_is_own_payoff(self):
        """Prompt must frame responder as one-round payoff maximizer."""
        prompt = build_responder_prompt(_responder_obs())
        lower = prompt.lower()
        assert "maximize your own payoff" in lower

    def test_does_not_reveal_true_pie(self):
        """True pie must remain hidden from the responder prompt."""
        obs = _responder_obs(claimed_pie=80.0, offer=30.0)
        prompt = build_responder_prompt(obs)
        assert "true_pie" not in prompt.lower()
        assert "hidden" in prompt.lower() or "cannot" in prompt.lower()


# ---------------------------------------------------------------------------
# P1 fix: configured audit_prob and lie_penalty reach LLM prompts
# ---------------------------------------------------------------------------

class TestConfiguredValuesInPrompts:
    """Verify that non-zero audit_prob and lie_penalty from the environment
    flow through the observation schema and appear verbatim in the prompts."""

    def _obs_with_audit(self, audit_prob: float = 0.25, lie_penalty: float = 25.0):
        return ProposerObservation(
            true_pie=100.0,
            pie_range=(50.0, 150.0),
            round_index=0,
            audit_prob=audit_prob,
            lie_penalty=lie_penalty,
        )

    def _resp_obs_with_audit(self, audit_prob: float = 0.25, lie_penalty: float = 25.0):
        return ResponderObservation(
            claimed_pie=100.0,
            offer=40.0,
            pie_range=(50.0, 150.0),
            round_index=0,
            audit_prob=audit_prob,
            lie_penalty=lie_penalty,
        )

    def test_proposer_prompt_shows_configured_audit_prob(self):
        obs = self._obs_with_audit(audit_prob=0.25)
        prompt = build_proposer_prompt(obs)
        assert "25%" in prompt

    def test_proposer_prompt_shows_configured_lie_penalty(self):
        obs = self._obs_with_audit(lie_penalty=25.0)
        prompt = build_proposer_prompt(obs)
        assert "25.00" in prompt

    def test_proposer_prompt_zero_audit_prob_shows_zero(self):
        obs = self._obs_with_audit(audit_prob=0.0)
        prompt = build_proposer_prompt(obs)
        assert "0%" in prompt

    def test_responder_prompt_shows_configured_audit_prob(self):
        obs = self._resp_obs_with_audit(audit_prob=0.25)
        prompt = build_responder_prompt(obs)
        assert "25%" in prompt

    def test_responder_prompt_shows_configured_lie_penalty(self):
        obs = self._resp_obs_with_audit(lie_penalty=25.0)
        prompt = build_responder_prompt(obs)
        assert "25.00" in prompt

    def test_env_populates_audit_prob_in_proposer_obs(self):
        from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
        env = HiddenPieAuditEnv(audit_prob=0.25, lie_penalty=25.0, rng_seed=1)
        _, obs = env.proposer_observation()
        assert obs.audit_prob == 0.25
        assert obs.lie_penalty == 25.0

    def test_env_populates_audit_prob_in_responder_obs(self):
        from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
        from ultimatum_arena.schemas import ProposerAction
        env = HiddenPieAuditEnv(audit_prob=0.25, lie_penalty=25.0, rng_seed=1)
        env.proposer_observation()
        obs = env.responder_observation(
            ProposerAction(claimed_pie=100.0, offer=40.0, public_message="")
        )
        assert obs.audit_prob == 0.25
        assert obs.lie_penalty == 25.0

    def test_end_to_end_configured_values_in_prompt_metadata(self):
        """Full run_experiment path: configured values appear in stored prompt metadata."""
        from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
        from ultimatum_arena.runners.basic import run_experiment
        env = HiddenPieAuditEnv(audit_prob=0.25, lie_penalty=25.0, rng_seed=1)
        results, _ = run_experiment(
            LLMProposer(FakeLLMClient()),
            LLMResponder(FakeLLMClient(responses=['{"accept": true}'])),
            env,
            n_rounds=1,
        )
        meta = results[0].metadata
        assert "25%" in meta["proposer_prompt"]
        assert "25.00" in meta["proposer_prompt"]
        assert "25%" in meta["responder_prompt"]
        assert "25.00" in meta["responder_prompt"]


# ---------------------------------------------------------------------------
# Task A: Proposer strategy profiles
# ---------------------------------------------------------------------------

class TestLLMProposerStrategy:
    """Tests for the strategy= parameter on LLMProposer."""

    def test_default_strategy_is_honest_fair(self):
        proposer = LLMProposer(FakeLLMClient())
        assert proposer.strategy == "honest_fair"

    def test_strategy_property_reflects_constructor_arg(self):
        for strategy in VALID_STRATEGIES:
            proposer = LLMProposer(FakeLLMClient(), strategy=strategy)
            assert proposer.strategy == strategy

    def test_invalid_strategy_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            LLMProposer(FakeLLMClient(), strategy="aggressive")

    def test_all_valid_strategies_accepted(self):
        for strategy in VALID_STRATEGIES:
            LLMProposer(FakeLLMClient(), strategy=strategy)  # must not raise

    def test_honest_fair_prompt_reaches_client(self):
        client = FakeLLMClient()
        proposer = LLMProposer(client, strategy="honest_fair")
        proposer.act(_proposer_obs())
        assert "HONEST AND FAIR" in client.calls[0]

    def test_self_interested_prompt_reaches_client(self):
        client = FakeLLMClient()
        proposer = LLMProposer(client, strategy="self_interested")
        proposer.act(_proposer_obs())
        assert "SELF-INTERESTED" in client.calls[0]

    def test_deceptive_prompt_reaches_client(self):
        client = FakeLLMClient()
        proposer = LLMProposer(client, strategy="deceptive")
        proposer.act(_proposer_obs())
        assert "DECEPTIVE" in client.calls[0]

    def test_strategy_prompt_distinct_from_default(self):
        """Deceptive and self-interested prompts must differ from honest_fair."""
        obs = _proposer_obs()
        honest_prompt = build_proposer_prompt(obs, strategy="honest_fair")
        deceptive_prompt = build_proposer_prompt(obs, strategy="deceptive")
        self_interested_prompt = build_proposer_prompt(obs, strategy="self_interested")
        assert honest_prompt != deceptive_prompt
        assert honest_prompt != self_interested_prompt
        assert deceptive_prompt != self_interested_prompt

    def test_default_build_prompt_matches_honest_fair(self):
        """build_proposer_prompt() with no strategy arg == strategy='honest_fair'."""
        obs = _proposer_obs()
        assert build_proposer_prompt(obs) == build_proposer_prompt(obs, strategy="honest_fair")


class TestStrategyPromptContent:
    """Check that each strategy section contains the expected key phrases."""

    def test_honest_fair_section_present(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="honest_fair")
        assert "HONEST AND FAIR" in prompt

    def test_honest_fair_instructs_truthful_claim(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="honest_fair")
        lower = prompt.lower()
        assert "honest" in lower or "equal to the true pie" in lower

    def test_self_interested_section_present(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="self_interested")
        assert "SELF-INTERESTED" in prompt

    def test_self_interested_instructs_minimum_offer(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="self_interested")
        lower = prompt.lower()
        assert "minimum" in lower or "maximise" in lower or "maximize" in lower

    def test_deceptive_section_present(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="deceptive")
        assert "DECEPTIVE" in prompt

    def test_deceptive_instructs_underreporting(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="deceptive")
        lower = prompt.lower()
        assert "underreport" in lower or "below the true pie" in lower or "60-70%" in lower

    def test_all_strategies_include_no_placeholder_warning(self):
        """Every strategy must warn against outputting placeholder values."""
        obs = _proposer_obs()
        for strategy in VALID_STRATEGIES:
            prompt = build_proposer_prompt(obs, strategy=strategy)
            lower = prompt.lower()
            assert "do not" in lower or "don't" in lower or "placeholder" in lower, (
                f"Strategy '{strategy}' prompt is missing placeholder warning"
            )

    def test_all_strategies_include_json_instruction(self):
        obs = _proposer_obs()
        for strategy in VALID_STRATEGIES:
            prompt = build_proposer_prompt(obs, strategy=strategy)
            assert "claimed_pie" in prompt
            assert "json" in prompt.lower()

    def test_valid_strategies_constant_matches_hints(self):
        """VALID_STRATEGIES must be consistent with the hint dict."""
        from ultimatum_arena.llm.prompts import _STRATEGY_HINTS
        assert VALID_STRATEGIES == frozenset(_STRATEGY_HINTS.keys())


# ---------------------------------------------------------------------------
# risk_aware strategy
# ---------------------------------------------------------------------------

class TestRiskAwareStrategy:
    def test_risk_aware_in_valid_strategies(self):
        assert "risk_aware" in VALID_STRATEGIES

    def test_llm_proposer_accepts_risk_aware(self):
        LLMProposer(FakeLLMClient(), strategy="risk_aware")  # must not raise

    def test_risk_aware_prompt_contains_header(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="risk_aware")
        assert "RISK-AWARE" in prompt

    def test_risk_aware_prompt_contains_expected_audit_cost(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="risk_aware")
        assert "expected audit cost" in prompt.lower()

    def test_risk_aware_prompt_mentions_audit(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="risk_aware")
        assert "audit" in prompt.lower()

    def test_risk_aware_prompt_mentions_penalty(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="risk_aware")
        assert "penalty" in prompt.lower()

    def test_risk_aware_prompt_allows_honest_behavior(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="risk_aware")
        lower = prompt.lower()
        assert "honest" in lower or "report honestly" in lower

    def test_risk_aware_prompt_allows_underclaiming(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="risk_aware")
        lower = prompt.lower()
        assert "underclaim" in lower or "underclaiming" in lower

    def test_risk_aware_prompt_distinct_from_all_other_strategies(self):
        obs = _proposer_obs()
        risk_aware_prompt = build_proposer_prompt(obs, strategy="risk_aware")
        for other in ("honest_fair", "self_interested", "deceptive"):
            assert risk_aware_prompt != build_proposer_prompt(obs, strategy=other)

    def test_risk_aware_reaches_client(self):
        client = FakeLLMClient()
        proposer = LLMProposer(client, strategy="risk_aware")
        proposer.act(_proposer_obs())
        assert "RISK-AWARE" in client.calls[0]

    def test_risk_aware_prompt_no_placeholder_warning(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="risk_aware")
        lower = prompt.lower()
        assert "do not" in lower or "don't" in lower or "placeholder" in lower


# ---------------------------------------------------------------------------
# expected_value strategy
# ---------------------------------------------------------------------------

class TestExpectedValueStrategy:
    def test_expected_value_in_valid_strategies(self):
        assert "expected_value" in VALID_STRATEGIES

    def test_llm_proposer_accepts_expected_value(self):
        LLMProposer(FakeLLMClient(), strategy="expected_value")  # must not raise

    def test_expected_value_prompt_contains_header(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="expected_value")
        assert "EXPECTED-VALUE" in prompt

    def test_expected_value_prompt_mentions_maximize_expected_payoff(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="expected_value")
        lower = prompt.lower()
        assert "maximize expected proposer payoff" in lower

    def test_expected_value_prompt_mentions_honest(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="expected_value")
        assert "honest" in prompt.lower()

    def test_expected_value_prompt_mentions_underclaim(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="expected_value")
        assert "underclaim" in prompt.lower()

    def test_expected_value_prompt_mentions_expected_audit_cost(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="expected_value")
        assert "expected audit cost" in prompt.lower()

    def test_expected_value_prompt_mentions_formula(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="expected_value")
        assert "audit_probability * lie_penalty" in prompt

    def test_expected_value_prompt_distinct_from_all_other_strategies(self):
        obs = _proposer_obs()
        ev_prompt = build_proposer_prompt(obs, strategy="expected_value")
        for other in ("honest_fair", "self_interested", "deceptive", "risk_aware"):
            assert ev_prompt != build_proposer_prompt(obs, strategy=other)

    def test_expected_value_reaches_client(self):
        client = FakeLLMClient()
        proposer = LLMProposer(client, strategy="expected_value")
        proposer.act(_proposer_obs())
        assert "EXPECTED-VALUE" in client.calls[0]

    def test_expected_value_prompt_no_placeholder_warning(self):
        prompt = build_proposer_prompt(_proposer_obs(), strategy="expected_value")
        lower = prompt.lower()
        assert "do not" in lower or "don't" in lower or "placeholder" in lower

    def test_invalid_strategy_still_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            LLMProposer(FakeLLMClient(), strategy="expected_value_extra")
