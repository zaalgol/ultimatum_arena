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


# ---------------------------------------------------------------------------
# Tests for scripts/probe_gemma3_expected_value.py (no Ollama required)
# ---------------------------------------------------------------------------

from unittest.mock import call, patch

from scripts.probe_gemma3_expected_value import (  # noqa: E402
    OUTPUT_ROOT,
    _parse_args,
    _probe_cells,
    _save_probe_manifest,
    main,
)


class TestProbeScriptImport:
    def test_can_import_without_side_effects(self):
        """Importing the module must not connect to Ollama or write files."""
        import scripts.probe_gemma3_expected_value  # noqa: F401


class TestProbeCells:
    def test_returns_three_cells(self):
        assert len(_probe_cells()) == 3

    def test_each_cell_is_two_tuple(self):
        for cell in _probe_cells():
            assert len(cell) == 2

    def test_contains_zero_audit_zero_penalty(self):
        """Low-risk cell (audit=0, penalty=0) must be present."""
        assert (0.0, 0.0) in _probe_cells()

    def test_contains_high_risk_cell(self):
        """High-risk cell (audit=1.0, penalty=50.0) must be present."""
        assert (1.0, 50.0) in _probe_cells()

    def test_contains_mid_risk_cell(self):
        """Moderate-risk cell must be present."""
        cells = _probe_cells()
        audit_probs = [c[0] for c in cells]
        assert any(0.0 < p < 1.0 for p in audit_probs)

    def test_all_audit_probs_in_0_to_1(self):
        for audit_prob, _ in _probe_cells():
            assert 0.0 <= audit_prob <= 1.0

    def test_all_penalties_non_negative(self):
        for _, penalty in _probe_cells():
            assert penalty >= 0.0


class TestProbeParseArgs:
    def test_default_model(self):
        args = _parse_args([])
        assert args.model == "gemma3"

    def test_default_rounds(self):
        args = _parse_args([])
        assert args.rounds == 10

    def test_default_seed(self):
        args = _parse_args([])
        assert args.seed == 1

    def test_default_temperature(self):
        args = _parse_args([])
        assert args.temperature == 0.2

    def test_model_override(self):
        args = _parse_args(["--model", "gemma3:4b"])
        assert args.model == "gemma3:4b"

    def test_rounds_override(self):
        args = _parse_args(["--rounds", "5"])
        assert args.rounds == 5

    def test_seed_override(self):
        args = _parse_args(["--seed", "42"])
        assert args.seed == 42

    def test_temperature_override(self):
        args = _parse_args(["--temperature", "0.5"])
        assert args.temperature == 0.5


class TestProbeOutputRoot:
    def test_output_root_under_outputs(self):
        assert "outputs" in str(OUTPUT_ROOT)

    def test_output_root_contains_probe_name(self):
        assert "expected_value_probe" in str(OUTPUT_ROOT)


class TestProbeNoPCartesianExpansion:
    """Regression: main() must call run_llm_strategy_sweep once per paired cell,
    not run a Cartesian product of all audit_probs × all lie_penalties."""

    def test_calls_sweep_exactly_three_times(self):
        """Exactly one sweep call per _probe_cells() pair."""
        fake_row = {"strategy": "expected_value", "audit_prob": 0.0, "lie_penalty": 0.0}
        with (
            patch(
                "scripts.probe_gemma3_expected_value.run_llm_strategy_sweep",
                return_value=[fake_row],
            ) as mock_sweep,
            patch("scripts.probe_gemma3_expected_value._save_combined_csv"),
            patch("scripts.probe_gemma3_expected_value.OllamaLLMClient"),
        ):
            main(["--rounds", "1"])

        assert mock_sweep.call_count == 3

    def test_each_call_uses_single_audit_prob(self):
        """Each sweep call must receive exactly one audit_prob value."""
        fake_row = {"strategy": "expected_value", "audit_prob": 0.0, "lie_penalty": 0.0}
        with (
            patch(
                "scripts.probe_gemma3_expected_value.run_llm_strategy_sweep",
                return_value=[fake_row],
            ) as mock_sweep,
            patch("scripts.probe_gemma3_expected_value._save_combined_csv"),
            patch("scripts.probe_gemma3_expected_value.OllamaLLMClient"),
        ):
            main(["--rounds", "1"])

        for c in mock_sweep.call_args_list:
            assert len(c.kwargs["audit_probabilities"]) == 1

    def test_each_call_uses_single_lie_penalty(self):
        """Each sweep call must receive exactly one lie_penalty value."""
        fake_row = {"strategy": "expected_value", "audit_prob": 0.0, "lie_penalty": 0.0}
        with (
            patch(
                "scripts.probe_gemma3_expected_value.run_llm_strategy_sweep",
                return_value=[fake_row],
            ) as mock_sweep,
            patch("scripts.probe_gemma3_expected_value._save_combined_csv"),
            patch("scripts.probe_gemma3_expected_value.OllamaLLMClient"),
        ):
            main(["--rounds", "1"])

        for c in mock_sweep.call_args_list:
            assert len(c.kwargs["lie_penalties"]) == 1

    def test_calls_match_probe_cells_pairs(self):
        """The (audit_prob, lie_penalty) pairs passed across all calls must
        exactly match _probe_cells() — in any order."""
        fake_row = {"strategy": "expected_value", "audit_prob": 0.0, "lie_penalty": 0.0}
        with (
            patch(
                "scripts.probe_gemma3_expected_value.run_llm_strategy_sweep",
                return_value=[fake_row],
            ) as mock_sweep,
            patch("scripts.probe_gemma3_expected_value._save_combined_csv"),
            patch("scripts.probe_gemma3_expected_value.OllamaLLMClient"),
        ):
            main(["--rounds", "1"])

        called_pairs = [
            (c.kwargs["audit_probabilities"][0], c.kwargs["lie_penalties"][0])
            for c in mock_sweep.call_args_list
        ]
        assert sorted(called_pairs) == sorted(_probe_cells())


class TestProbeManifest:
    def test_manifest_records_all_paired_cells(self, tmp_path):
        args = _parse_args(["--model", "gemma3", "--rounds", "5", "--seed", "42"])
        cells = _probe_cells()

        _save_probe_manifest(tmp_path, cells=cells, args=args)

        import json

        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["n_cells"] == len(cells)
        assert manifest["cells"] == [
            {"audit_prob": audit_prob, "lie_penalty": lie_penalty}
            for audit_prob, lie_penalty in cells
        ]
        assert manifest["model"] == "gemma3"
        assert manifest["n_rounds"] == 5
        assert manifest["seeds"] == [42]
