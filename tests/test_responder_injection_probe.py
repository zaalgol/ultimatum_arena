"""Tests for scripts/probe_responder_injection.py (no live Ollama/OpenAI).

The controlled probe is exercised with fake responders / clients so the wiring,
flip detection, and output writing are verified deterministically.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from scripts.probe_responder_injection import (  # noqa: E402
    INJECTION_MESSAGE,
    NEUTRAL_MESSAGE,
    OUTPUT_ROOT,
    _accept_count,
    _default_modes,
    _default_ratios,
    _injection_flips,
    main,
    parse_args,
    run_probe,
)
from ultimatum_arena.schemas import ResponderAction


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _InjectionSensitiveResponder:
    """Accepts iff the observation's public_message carries the injection."""

    def act(self, obs):
        return ResponderAction(accept="Ignore previous instructions" in obs.public_message)


class _ConditionAwareFakeClient:
    """LLMClient fake: accepts when the prompt contains the injection text."""

    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        if "Ignore previous instructions" in prompt:
            return '{"accept": true}'
        return '{"accept": false}'


# ---------------------------------------------------------------------------
# parse_args / defaults
# ---------------------------------------------------------------------------

class TestParseArgs:
    def test_default_provider(self):
        assert parse_args([]).provider == "ollama"

    def test_default_model(self):
        assert parse_args([]).model == "gemma3"

    def test_default_temperature_is_zero(self):
        assert parse_args([]).temperature == 0.0

    def test_default_repeats(self):
        assert parse_args([]).repeats == 3

    def test_default_modes(self):
        assert parse_args([]).modes == ["naive", "standard", "robust"]

    def test_default_ratios(self):
        assert parse_args([]).ratios == [0.05, 0.12, 0.18, 0.25, 0.40]

    def test_modes_override(self):
        assert parse_args(["--modes", "robust", "naive"]).modes == ["robust", "naive"]

    def test_invalid_mode_rejected(self):
        with pytest.raises(SystemExit):
            parse_args(["--modes", "bogus"])

    def test_ratios_override(self):
        assert parse_args(["--ratios", "0.1", "0.3"]).ratios == [0.1, 0.3]

    def test_provider_openai(self):
        assert parse_args(["--provider", "openai"]).provider == "openai"


class TestConstants:
    def test_injection_message_has_attack_phrases(self):
        assert "Ignore previous instructions" in INJECTION_MESSAGE
        assert "You must accept" in INJECTION_MESSAGE

    def test_neutral_message_has_no_attack_phrases(self):
        assert "ignore" not in NEUTRAL_MESSAGE.lower()
        assert "must accept" not in NEUTRAL_MESSAGE.lower()

    def test_default_helpers_return_copies(self):
        a, b = _default_ratios(), _default_ratios()
        a.append(99.0)
        assert b == [0.05, 0.12, 0.18, 0.25, 0.40]
        assert _default_modes() == ["naive", "standard", "robust"]

    def test_output_root(self):
        assert "outputs" in str(OUTPUT_ROOT)
        assert "responder_injection_probe" in str(OUTPUT_ROOT)


# ---------------------------------------------------------------------------
# run_probe wiring + flip detection
# ---------------------------------------------------------------------------

class TestRunProbe:
    def _run(self, ratios, modes, repeats=2):
        return run_probe(
            responder_builder=lambda mode: _InjectionSensitiveResponder(),
            modes=modes,
            ratios=ratios,
            repeats=repeats,
            claimed_pie=100.0,
            audit_prob=0.25,
            lie_penalty=25.0,
        )

    def test_row_count(self):
        results = self._run([0.1, 0.3], ["robust"])
        # 2 conditions x 2 ratios x 1 mode
        assert len(results) == 4

    def test_injection_accepts_neutral_rejects(self):
        results = self._run([0.1], ["robust"], repeats=3)
        neutral = [r for r in results if r["condition"] == "neutral"][0]
        injection = [r for r in results if r["condition"] == "injection"][0]
        assert neutral["accept_count"] == 0
        assert injection["accept_count"] == 3

    def test_acceptance_rate_computed(self):
        results = self._run([0.1], ["robust"], repeats=4)
        injection = [r for r in results if r["condition"] == "injection"][0]
        assert injection["acceptance_rate"] == 1.0

    def test_injection_flips_counts_all_ratios(self):
        ratios = [0.1, 0.2, 0.3]
        results = self._run(ratios, ["robust", "naive"])
        flips = _injection_flips(results, ["robust", "naive"], ratios)
        # Every ratio flips reject->accept for this responder.
        assert flips == {"robust": 3, "naive": 3}

    def test_accept_count_float_tolerance(self):
        # 0.1 + 0.2 != 0.3 exactly; lookup must still find the row.
        results = self._run([0.1 + 0.2], ["robust"])
        assert _accept_count(results, "injection", 0.3, "robust") == 2


# ---------------------------------------------------------------------------
# main() end-to-end with patched client (writes to redirected tmp OUTPUT_ROOT)
# ---------------------------------------------------------------------------

class TestMain:
    def test_writes_outputs_and_flips(self, tmp_path):
        with patch(
            "scripts.probe_responder_injection.OllamaLLMClient", _ConditionAwareFakeClient
        ), patch("scripts.probe_responder_injection.OUTPUT_ROOT", tmp_path):
            main(["--repeats", "1", "--ratios", "0.1", "0.4", "--modes", "robust", "naive"])

        run_dir = next(tmp_path.iterdir())
        results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        # 2 conditions x 2 ratios x 2 modes
        assert len(results) == 8
        # The fake accepts only under injection, so every ratio flips for both modes.
        assert manifest["injection_flips_by_mode"] == {"robust": 2, "naive": 2}
        assert manifest["provider"] == "ollama"

    def test_openai_provider_uses_patched_client(self, tmp_path):
        with patch(
            "scripts.probe_responder_injection.OpenAIResponsesClient", _ConditionAwareFakeClient
        ), patch("scripts.probe_responder_injection.OUTPUT_ROOT", tmp_path):
            main(["--provider", "openai", "--model", "gpt-5.4-mini", "--repeats", "1",
                  "--ratios", "0.2", "--modes", "standard"])

        run_dir = next(tmp_path.iterdir())
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["provider"] == "openai"
        assert manifest["model"] == "gpt-5.4-mini"
