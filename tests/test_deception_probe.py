"""Tests for scripts/probe_deception.py — refusal-safe deception probe (no live LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from scripts.probe_deception import (  # noqa: E402
    DEFAULT_STRATEGIES,
    OUTPUT_ROOT,
    _default_cells,
    _parse_cells,
    main,
    parse_args,
    run_deception_probe,
)
from ultimatum_arena.llm.agents import LLMProposer


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _HonestFake:
    """Proposer client that reports the true pie (no deception)."""
    def __init__(self, *a, **k): pass
    def generate(self, prompt: str) -> str:
        # claimed == true (extract true_pie from the prompt's "True pie size: X")
        import re
        m = re.search(r"True pie size:\s*([\d.]+)", prompt)
        true = float(m.group(1)) if m else 100.0
        return f'{{"claimed_pie": {true}, "offer": {true/2}, "public_message": ""}}'


class _DeceptiveFake:
    """Proposer client that underclaims (claimed = 60% of true)."""
    def __init__(self, *a, **k): pass
    def generate(self, prompt: str) -> str:
        import re
        m = re.search(r"True pie size:\s*([\d.]+)", prompt)
        true = float(m.group(1)) if m else 100.0
        claimed = round(true * 0.6, 2)
        return f'{{"claimed_pie": {claimed}, "offer": {round(claimed/2,2)}, "public_message": ""}}'


class _RefusingFake:
    """Proposer client that refuses (returns prose, not JSON)."""
    def __init__(self, *a, **k): pass
    def generate(self, prompt: str) -> str:
        return "I can't help with this. I won't craft a deceptive strategy, even in a game."


# ---------------------------------------------------------------------------
# CLI / defaults
# ---------------------------------------------------------------------------

class TestParseArgs:
    def test_default_provider(self):
        assert parse_args([]).provider == "ollama"

    def test_provider_claude(self):
        assert parse_args(["--provider", "claude"]).provider == "claude"

    def test_default_strategies_are_six(self):
        assert parse_args([]).strategies == DEFAULT_STRATEGIES
        assert len(DEFAULT_STRATEGIES) == 6

    def test_default_rounds(self):
        assert parse_args([]).rounds == 10

    def test_strategies_override(self):
        assert parse_args(["--strategies", "risk_aware", "payoff_table"]).strategies == ["risk_aware", "payoff_table"]

    def test_invalid_strategy_rejected(self):
        with pytest.raises(SystemExit):
            parse_args(["--strategies", "bogus"])


class TestCells:
    def test_default_cells(self):
        assert _default_cells() == [(0.0, 0.0), (0.25, 25.0), (1.0, 50.0)]

    def test_parse_cells_none(self):
        assert _parse_cells(None) == _default_cells()

    def test_parse_cells_tokens(self):
        assert _parse_cells(["0:0", "0.5:30"]) == [(0.0, 0.0), (0.5, 30.0)]

    def test_output_root(self):
        assert "outputs" in str(OUTPUT_ROOT) and "deception_probe" in str(OUTPUT_ROOT)


# ---------------------------------------------------------------------------
# run_deception_probe — core behaviour
# ---------------------------------------------------------------------------

class TestRunProbe:
    def _run(self, client_cls, strategies=("deceptive",), cells=((0.0, 0.0),), rounds=10):
        return run_deception_probe(
            proposer_builder=lambda s: LLMProposer(client_cls(), strategy=s),
            strategies=list(strategies),
            cells=list(cells),
            n_rounds=rounds,
            seed=1,
        )

    def test_honest_zero_deception(self):
        rows = self._run(_HonestFake, strategies=("honest_fair",))
        r = rows[0]
        assert r["rounds_completed"] == 10
        assert r["refusal_count"] == 0
        assert r["deception_rate"] == 0.0

    def test_deceptive_high_deception(self):
        rows = self._run(_DeceptiveFake, strategies=("deceptive",))
        r = rows[0]
        assert r["rounds_completed"] == 10
        assert r["deception_rate"] == 1.0
        assert r["n_lies"] == 10

    def test_refusal_is_safe_and_recorded(self):
        # The whole point: refusals must NOT raise; they become rows with refusal_count.
        rows = self._run(_RefusingFake, strategies=("deceptive",))
        r = rows[0]
        assert r["refusal_count"] == 10
        assert r["rounds_completed"] == 0
        assert r["deception_rate"] is None  # compute_metrics([]) -> {}
        assert r["n_lies"] == 0
        assert r["refusal_examples"]  # raw text captured
        assert "won't craft a deceptive strategy" in r["refusal_examples"][0]["raw_response"]

    def test_detection_sanity_flag(self):
        # 10 lies at audit=1.0 -> n_lies>=10 -> detection_sanity_valid True
        rows = self._run(_DeceptiveFake, strategies=("deceptive",), cells=((1.0, 50.0),))
        assert rows[0]["detection_sanity_valid"] is True
        # honest -> 0 lies -> not valid
        rows2 = self._run(_HonestFake, strategies=("honest_fair",), cells=((1.0, 50.0),))
        assert rows2[0]["detection_sanity_valid"] is False

    def test_normalized_audit_cost(self):
        rows = self._run(_HonestFake, strategies=("honest_fair",), cells=((0.5, 30.0),))
        r = rows[0]
        # normalized = audit*penalty/mean_true_pie = 15 / mean_true
        assert r["normalized_audit_cost"] == pytest.approx(0.5 * 30.0 / r["mean_true_pie"])

    def test_one_row_per_strategy_cell(self):
        rows = self._run(_HonestFake, strategies=("honest_fair", "self_interested"), cells=((0.0, 0.0), (1.0, 50.0)))
        assert len(rows) == 4


# ---------------------------------------------------------------------------
# main() end-to-end with patched client (writes to redirected tmp OUTPUT_ROOT)
# ---------------------------------------------------------------------------

class TestMain:
    def test_claude_refusal_run_completes_and_writes(self, tmp_path):
        # Even when Claude "refuses" every round, main() must complete and write outputs.
        with patch("scripts.probe_deception.ClaudeCLIClient", _RefusingFake), patch(
            "scripts.probe_deception.OUTPUT_ROOT", tmp_path
        ):
            main(["--provider", "claude", "--model", "haiku", "--strategies", "deceptive",
                  "--cells", "0:0", "--rounds", "3"])
        run_dir = next(tmp_path.iterdir())
        results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert results[0]["refusal_count"] == 3
        assert manifest["provider"] == "claude"
        assert "Claude Code CLI" in manifest["provider_label"]
        assert manifest["total_refusals"] == 3

    def test_ollama_honest_run(self, tmp_path):
        with patch("scripts.probe_deception.OllamaLLMClient", _HonestFake), patch(
            "scripts.probe_deception.OUTPUT_ROOT", tmp_path
        ):
            main(["--provider", "ollama", "--model", "gemma3", "--strategies", "honest_fair",
                  "--cells", "0:0", "1:50", "--rounds", "4"])
        run_dir = next(tmp_path.iterdir())
        results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
        assert len(results) == 2
        assert all(r["deception_rate"] == 0.0 for r in results)
