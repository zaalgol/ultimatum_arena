"""Tests for run_llm_strategy_sweep."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from ultimatum_arena.llm.client import FakeLLMClient
from ultimatum_arena.runners.llm_sweep import _LLM_CONFIG_FIELDS, run_llm_strategy_sweep

_PROPOSER_RESPONSE = '{"claimed_pie": 100.0, "offer": 50.0, "public_message": "test"}'
_RESPONDER_RESPONSE = '{"accept": true}'


def _proposer_factory() -> FakeLLMClient:
    return FakeLLMClient(responses=[_PROPOSER_RESPONSE])


def _responder_factory() -> FakeLLMClient:
    return FakeLLMClient(responses=[_RESPONDER_RESPONSE])


# ---------------------------------------------------------------------------
# Return value
# ---------------------------------------------------------------------------

class TestRunLLMStrategySweepReturnValue:
    def test_row_count_single_cell(self):
        rows = run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[42],
            n_rounds=2,
        )
        assert len(rows) == 1

    def test_row_count_multiple_dimensions(self):
        rows = run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair", "deceptive"],
            audit_probabilities=[0.0, 0.5],
            lie_penalties=[0.0, 10.0],
            seeds=[1, 2],
            n_rounds=2,
        )
        # 2 × 2 × 2 × 2 = 16
        assert len(rows) == 16

    def test_config_fields_present(self):
        rows = run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.25],
            lie_penalties=[10.0],
            seeds=[7],
            n_rounds=2,
        )
        row = rows[0]
        assert row["strategy"] == "honest_fair"
        assert row["audit_prob"] == pytest.approx(0.25)
        assert row["lie_penalty"] == pytest.approx(10.0)
        assert row["seed"] == 7
        assert row["n_rounds"] == 2
        assert row["proposer_class"] == "LLMProposer"
        assert row["responder_class"] == "LLMResponder"

    def test_metric_fields_present(self):
        rows = run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[42],
            n_rounds=3,
        )
        row = rows[0]
        for key in (
            "acceptance_rate",
            "deception_rate",
            "mean_offer",
            "proposer_mean_payoff",
            "responder_mean_payoff",
        ):
            assert key in row, f"missing metric '{key}'"

    def test_strategy_values_in_rows(self):
        strategies = ["honest_fair", "self_interested", "deceptive"]
        rows = run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=strategies,
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
        )
        assert len(rows) == 3
        assert {r["strategy"] for r in rows} == set(strategies)

    def test_each_row_records_its_own_seed(self):
        rows = run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[11, 22, 33],
            n_rounds=2,
        )
        assert {r["seed"] for r in rows} == {11, 22, 33}

    def test_model_none_for_fake_client(self):
        rows = run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
        )
        assert rows[0]["model"] is None

    def test_temperature_none_for_fake_client(self):
        rows = run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
        )
        assert rows[0]["temperature"] is None

    def test_no_output_when_output_dir_is_none(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
            output_dir=None,
        )
        assert not list(tmp_path.glob("*"))


# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------

class TestRunLLMStrategySweepOutput:
    def test_combined_csv_written(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
            output_dir=tmp_path,
        )
        assert (tmp_path / "combined_summary.csv").exists()

    def test_manifest_json_written(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.25],
            lie_penalties=[10.0],
            seeds=[42],
            n_rounds=3,
            output_dir=tmp_path,
        )
        manifest_path = tmp_path / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["strategies"] == ["honest_fair"]
        assert manifest["audit_probabilities"] == [0.25]
        assert manifest["lie_penalties"] == [10.0]
        assert manifest["seeds"] == [42]
        assert manifest["n_rounds"] == 3
        assert manifest["n_cells"] == 1

    def test_manifest_n_cells_matches_row_count(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair", "deceptive"],
            audit_probabilities=[0.0, 0.5],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
            output_dir=tmp_path,
        )
        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["n_cells"] == 4

    def test_runs_dir_created(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
            output_dir=tmp_path,
        )
        assert (tmp_path / "runs").is_dir()

    def test_per_run_jsonl_written(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
            output_dir=tmp_path,
        )
        assert len(list((tmp_path / "runs").glob("*.jsonl"))) == 1

    def test_per_run_summary_json_written(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
            output_dir=tmp_path,
        )
        assert len(list((tmp_path / "runs").glob("*_summary.json"))) == 1

    def test_run_file_count_matches_cells(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair", "deceptive"],
            audit_probabilities=[0.0, 0.5],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
            output_dir=tmp_path,
        )
        assert len(list((tmp_path / "runs").glob("*.jsonl"))) == 4

    def test_csv_row_count_matches_cells(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair", "self_interested"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1, 2],
            n_rounds=2,
            output_dir=tmp_path,
        )
        with (tmp_path / "combined_summary.csv").open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 4

    def test_csv_config_columns_come_first(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
            output_dir=tmp_path,
        )
        with (tmp_path / "combined_summary.csv").open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        assert fieldnames[: len(_LLM_CONFIG_FIELDS)] == _LLM_CONFIG_FIELDS

    def test_csv_contains_metric_columns(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=3,
            output_dir=tmp_path,
        )
        with (tmp_path / "combined_summary.csv").open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        for col in ("acceptance_rate", "deception_rate", "mean_offer"):
            assert col in fieldnames

    def test_run_names_contain_strategy(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["deceptive"],
            audit_probabilities=[0.25],
            lie_penalties=[10.0],
            seeds=[1],
            n_rounds=2,
            output_dir=tmp_path,
        )
        jsonl_files = list((tmp_path / "runs").glob("*.jsonl"))
        assert any("deceptive" in f.name for f in jsonl_files)

    def test_manifest_pie_range_recorded(self, tmp_path):
        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
            pie_range=(60.0, 140.0),
            output_dir=tmp_path,
        )
        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["pie_range"] == [60.0, 140.0]


# ---------------------------------------------------------------------------
# Factory call counting
# ---------------------------------------------------------------------------

class TestClientFactoryCalls:
    def test_proposer_factory_called_once_per_run(self):
        call_count = [0]

        def counting_proposer_factory():
            call_count[0] += 1
            return FakeLLMClient(responses=[_PROPOSER_RESPONSE])

        run_llm_strategy_sweep(
            proposer_client_factory=counting_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair", "deceptive"],
            audit_probabilities=[0.0, 0.5],
            lie_penalties=[0.0],
            seeds=[1, 2],
            n_rounds=2,
        )
        # 2 strategies × 2 audit_probs × 1 lie_penalty × 2 seeds = 8
        assert call_count[0] == 8

    def test_responder_factory_called_once_per_run(self):
        call_count = [0]

        def counting_responder_factory():
            call_count[0] += 1
            return FakeLLMClient(responses=[_RESPONDER_RESPONSE])

        run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=counting_responder_factory,
            strategies=["honest_fair"],
            audit_probabilities=[0.0, 0.5, 1.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
        )
        assert call_count[0] == 3


# ---------------------------------------------------------------------------
# Strategy validation
# ---------------------------------------------------------------------------

class TestStrategyValidation:
    def test_invalid_strategy_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            run_llm_strategy_sweep(
                proposer_client_factory=_proposer_factory,
                responder_client_factory=_responder_factory,
                strategies=["not_a_real_strategy"],
                audit_probabilities=[0.0],
                lie_penalties=[0.0],
                seeds=[1],
                n_rounds=2,
            )

    def test_all_valid_strategies_accepted(self):
        rows = run_llm_strategy_sweep(
            proposer_client_factory=_proposer_factory,
            responder_client_factory=_responder_factory,
            strategies=["honest_fair", "self_interested", "deceptive"],
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            seeds=[1],
            n_rounds=2,
        )
        assert len(rows) == 3


# ---------------------------------------------------------------------------
# Public import surface
# ---------------------------------------------------------------------------

class TestPublicImport:
    def test_importable_from_runners(self):
        from ultimatum_arena.runners import run_llm_strategy_sweep  # noqa: F401
