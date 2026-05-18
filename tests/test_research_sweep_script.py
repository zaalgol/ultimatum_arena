"""Pure argument-parsing tests for scripts/run_gemma3_research_sweep.py.

No Ollama required -- only parse_args and _PRESETS are tested.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the script importable without running main()
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from scripts.run_gemma3_research_sweep import _PRESETS, parse_args  # noqa: E402


class TestRiskPresetExists:
    def test_risk_preset_in_presets(self):
        assert "risk" in _PRESETS

    def test_risk_preset_includes_risk_aware_strategy(self):
        assert "risk_aware" in _PRESETS["risk"]["strategies"]

    def test_risk_preset_includes_honest_fair(self):
        assert "honest_fair" in _PRESETS["risk"]["strategies"]

    def test_risk_preset_includes_deceptive(self):
        assert "deceptive" in _PRESETS["risk"]["strategies"]

    def test_risk_preset_audit_probabilities(self):
        assert _PRESETS["risk"]["audit_probabilities"] == [0.0, 0.25, 0.5, 1.0]

    def test_risk_preset_lie_penalties(self):
        assert _PRESETS["risk"]["lie_penalties"] == [0.0, 25.0, 50.0]

    def test_risk_preset_seeds(self):
        assert _PRESETS["risk"]["seeds"] == [1, 2, 3]

    def test_risk_preset_total_runs(self):
        p = _PRESETS["risk"]
        total = (
            len(p["strategies"])
            * len(p["audit_probabilities"])
            * len(p["lie_penalties"])
            * len(p["seeds"])
        )
        assert total == 108

    def test_risk_preset_rounds(self):
        assert _PRESETS["risk"]["n_rounds"] == 50


class TestExistingPresetsUnchanged:
    def test_smoke_preset_still_exists(self):
        assert "smoke" in _PRESETS

    def test_research_preset_still_exists(self):
        assert "research" in _PRESETS

    def test_smoke_strategies_unchanged(self):
        assert _PRESETS["smoke"]["strategies"] == ["honest_fair", "deceptive"]

    def test_research_strategies_unchanged(self):
        assert _PRESETS["research"]["strategies"] == ["honest_fair", "self_interested", "deceptive"]


class TestParseArgsRiskPreset:
    def test_risk_is_accepted_preset(self):
        args = parse_args(["--preset", "risk"])
        assert args.preset == "risk"

    def test_risk_with_rounds_override(self):
        args = parse_args(["--preset", "risk", "--rounds", "10"])
        assert args.preset == "risk"
        assert args.rounds == 10

    def test_risk_with_seeds_override(self):
        args = parse_args(["--preset", "risk", "--seeds", "1"])
        assert args.seeds == [1]

    def test_invalid_preset_raises(self):
        with pytest.raises(SystemExit):
            parse_args(["--preset", "nonexistent"])

    def test_smoke_still_default(self):
        args = parse_args([])
        assert args.preset == "smoke"


class TestEvPresetExists:
    def test_ev_preset_in_presets(self):
        assert "ev" in _PRESETS

    def test_ev_preset_includes_expected_value(self):
        assert "expected_value" in _PRESETS["ev"]["strategies"]

    def test_ev_preset_includes_honest_fair(self):
        assert "honest_fair" in _PRESETS["ev"]["strategies"]

    def test_ev_preset_includes_deceptive(self):
        assert "deceptive" in _PRESETS["ev"]["strategies"]

    def test_ev_preset_includes_risk_aware(self):
        assert "risk_aware" in _PRESETS["ev"]["strategies"]

    def test_ev_preset_audit_probabilities(self):
        assert _PRESETS["ev"]["audit_probabilities"] == [0.0, 0.25, 0.5, 1.0]

    def test_ev_preset_lie_penalties(self):
        assert _PRESETS["ev"]["lie_penalties"] == [0.0, 25.0, 50.0]

    def test_ev_preset_seeds(self):
        assert _PRESETS["ev"]["seeds"] == [1, 2, 3]

    def test_ev_preset_rounds(self):
        assert _PRESETS["ev"]["n_rounds"] == 50

    def test_ev_preset_total_runs(self):
        p = _PRESETS["ev"]
        total = (
            len(p["strategies"])
            * len(p["audit_probabilities"])
            * len(p["lie_penalties"])
            * len(p["seeds"])
        )
        assert total == 144


class TestParseArgsEvPreset:
    def test_ev_is_accepted_preset(self):
        args = parse_args(["--preset", "ev"])
        assert args.preset == "ev"

    def test_ev_with_rounds_override(self):
        args = parse_args(["--preset", "ev", "--rounds", "10"])
        assert args.rounds == 10

    def test_ev_with_seeds_override(self):
        args = parse_args(["--preset", "ev", "--seeds", "1"])
        assert args.seeds == [1]
