"""Tests for sweep runner and CSV output."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ultimatum_arena.agents.proposers import HonestFairProposer, LyingGreedyProposer
from ultimatum_arena.agents.responders import ThresholdResponder
from ultimatum_arena.runners import run_audit_penalty_sweep, save_sweep_csv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _proposer_factory():
    return HonestFairProposer()


def _responder_factory():
    return ThresholdResponder()


_AUDIT_PROBS = [0.0, 0.5]
_LIE_PENALTIES = [0.0, 10.0]


# ---------------------------------------------------------------------------
# save_sweep_csv
# ---------------------------------------------------------------------------

class TestSaveSweepCsv:
    def test_empty_rows_writes_empty_file(self, tmp_path):
        out = tmp_path / "empty.csv"
        save_sweep_csv([], out)
        assert out.exists()
        assert out.read_text(encoding="utf-8") == ""

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "nested" / "dir" / "out.csv"
        save_sweep_csv([{"audit_prob": 0.1, "lie_penalty": 5.0, "n_rounds": 10,
                         "seed": 42, "proposer_class": "X", "responder_class": "Y",
                         "acceptance_rate": 1.0}], out)
        assert out.exists()

    def test_row_count_matches(self, tmp_path):
        rows = [
            {"audit_prob": 0.0, "lie_penalty": 0.0, "seed": 42, "n_rounds": 5,
             "proposer_class": "A", "responder_class": "B", "acceptance_rate": 1.0},
            {"audit_prob": 0.5, "lie_penalty": 10.0, "seed": 42, "n_rounds": 5,
             "proposer_class": "A", "responder_class": "B", "acceptance_rate": 0.8},
        ]
        out = tmp_path / "out.csv"
        save_sweep_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            reader = list(csv.DictReader(fh))
        assert len(reader) == 2

    def test_config_fields_come_first(self, tmp_path):
        rows = [{"audit_prob": 0.0, "lie_penalty": 0.0, "seed": 1, "n_rounds": 10,
                 "proposer_class": "P", "responder_class": "R", "some_metric": 0.5}]
        out = tmp_path / "out.csv"
        save_sweep_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        expected_prefix = ["audit_prob", "lie_penalty", "seed", "n_rounds",
                           "proposer_class", "responder_class"]
        assert fieldnames[:6] == expected_prefix

    def test_metric_fields_present(self, tmp_path):
        rows = [{"audit_prob": 0.0, "lie_penalty": 0.0, "seed": 1, "n_rounds": 10,
                 "proposer_class": "P", "responder_class": "R",
                 "acceptance_rate": 0.9, "deception_rate": 0.1}]
        out = tmp_path / "out.csv"
        save_sweep_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        assert "acceptance_rate" in fieldnames
        assert "deception_rate" in fieldnames

    def test_values_round_trip(self, tmp_path):
        rows = [{"audit_prob": 0.25, "lie_penalty": 5.0, "seed": 7, "n_rounds": 3,
                 "proposer_class": "P", "responder_class": "R", "acceptance_rate": 0.75}]
        out = tmp_path / "out.csv"
        save_sweep_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            data = list(csv.DictReader(fh))
        assert float(data[0]["audit_prob"]) == pytest.approx(0.25)
        assert float(data[0]["acceptance_rate"]) == pytest.approx(0.75)

    def test_fieldnames_union_across_all_rows(self, tmp_path):
        """Fieldnames must be collected from ALL rows, not just the first."""
        rows = [
            {"audit_prob": 0.0, "lie_penalty": 0.0, "seed": 1, "n_rounds": 5,
             "proposer_class": "P", "responder_class": "R", "metric_a": 1.0},
            {"audit_prob": 0.5, "lie_penalty": 0.0, "seed": 1, "n_rounds": 5,
             "proposer_class": "P", "responder_class": "R",
             "metric_a": 2.0, "metric_b": 3.0},
        ]
        out = tmp_path / "out.csv"
        save_sweep_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        assert "metric_b" in fieldnames


# ---------------------------------------------------------------------------
# run_audit_penalty_sweep — return value
# ---------------------------------------------------------------------------

class TestRunAuditPenaltySweepReturnValue:
    def test_row_count_equals_grid_size_single_seed(self):
        rows = run_audit_penalty_sweep(
            audit_probabilities=_AUDIT_PROBS,
            lie_penalties=_LIE_PENALTIES,
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=5,
            seeds=[42],
        )
        assert len(rows) == len(_AUDIT_PROBS) * len(_LIE_PENALTIES) * 1

    def test_row_count_equals_grid_size_multiple_seeds(self):
        rows = run_audit_penalty_sweep(
            audit_probabilities=[0.0, 0.5],
            lie_penalties=[0.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=3,
            seeds=[1, 2, 3],
        )
        assert len(rows) == 2 * 1 * 3

    def test_config_fields_present_in_rows(self):
        rows = run_audit_penalty_sweep(
            audit_probabilities=[0.2],
            lie_penalties=[5.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=3,
            seeds=[7],
        )
        row = rows[0]
        assert row["audit_prob"] == pytest.approx(0.2)
        assert row["lie_penalty"] == pytest.approx(5.0)
        assert row["seed"] == 7
        assert row["n_rounds"] == 3
        assert row["proposer_class"] == "HonestFairProposer"
        assert row["responder_class"] == "ThresholdResponder"

    def test_each_row_records_its_own_seed(self):
        rows = run_audit_penalty_sweep(
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=3,
            seeds=[11, 22],
        )
        seeds_in_rows = {row["seed"] for row in rows}
        assert seeds_in_rows == {11, 22}

    def test_metric_fields_present_in_rows(self):
        rows = run_audit_penalty_sweep(
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=5,
        )
        row = rows[0]
        for key in ("acceptance_rate", "deception_rate", "mean_offer",
                    "proposer_mean_payoff", "responder_mean_payoff"):
            assert key in row, f"expected key '{key}' in row"

    def test_default_seeds_produces_one_row_per_cell(self):
        rows = run_audit_penalty_sweep(
            audit_probabilities=[0.3],
            lie_penalties=[2.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=5,
        )
        assert len(rows) == 1
        assert rows[0]["seed"] == 42  # default seed

    def test_no_output_dir_returns_rows_without_error(self):
        rows = run_audit_penalty_sweep(
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=2,
            output_dir=None,
        )
        assert isinstance(rows, list)
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# run_audit_penalty_sweep — CSV output
# ---------------------------------------------------------------------------

class TestRunAuditPenaltySweepCsvOutput:
    def test_csv_file_written_when_output_dir_provided(self, tmp_path):
        run_audit_penalty_sweep(
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=3,
            output_dir=tmp_path,
            experiment_prefix="test_sweep",
        )
        assert (tmp_path / "test_sweep_summary.csv").exists()

    def test_csv_row_count_equals_returned_row_count(self, tmp_path):
        rows = run_audit_penalty_sweep(
            audit_probabilities=_AUDIT_PROBS,
            lie_penalties=_LIE_PENALTIES,
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=5,
            seeds=[42],
            output_dir=tmp_path,
        )
        csv_path = tmp_path / "sweep_summary.csv"
        with csv_path.open(newline="", encoding="utf-8") as fh:
            csv_rows = list(csv.DictReader(fh))
        assert len(csv_rows) == len(rows)

    def test_csv_contains_config_columns(self, tmp_path):
        run_audit_penalty_sweep(
            audit_probabilities=[0.1],
            lie_penalties=[1.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=3,
            output_dir=tmp_path,
        )
        csv_path = tmp_path / "sweep_summary.csv"
        with csv_path.open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        for col in ("audit_prob", "lie_penalty", "seed", "n_rounds",
                    "proposer_class", "responder_class"):
            assert col in fieldnames

    def test_csv_contains_metric_columns(self, tmp_path):
        run_audit_penalty_sweep(
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=5,
            output_dir=tmp_path,
        )
        csv_path = tmp_path / "sweep_summary.csv"
        with csv_path.open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        for col in ("acceptance_rate", "deception_rate", "mean_offer"):
            assert col in fieldnames

    def test_csv_config_columns_come_first(self, tmp_path):
        run_audit_penalty_sweep(
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=3,
            output_dir=tmp_path,
        )
        csv_path = tmp_path / "sweep_summary.csv"
        with csv_path.open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        assert fieldnames[:6] == [
            "audit_prob", "lie_penalty", "seed", "n_rounds",
            "proposer_class", "responder_class",
        ]

    def test_csv_values_match_returned_rows(self, tmp_path):
        rows = run_audit_penalty_sweep(
            audit_probabilities=[0.25],
            lie_penalties=[3.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=10,
            output_dir=tmp_path,
        )
        csv_path = tmp_path / "sweep_summary.csv"
        with csv_path.open(newline="", encoding="utf-8") as fh:
            csv_rows = list(csv.DictReader(fh))
        assert float(csv_rows[0]["audit_prob"]) == pytest.approx(rows[0]["audit_prob"])
        assert float(csv_rows[0]["acceptance_rate"]) == pytest.approx(
            rows[0]["acceptance_rate"]
        )

    def test_no_csv_written_without_output_dir(self, tmp_path):
        run_audit_penalty_sweep(
            audit_probabilities=[0.0],
            lie_penalties=[0.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=3,
            output_dir=None,
        )
        assert not list(tmp_path.glob("*.csv"))

    def test_different_proposer_class_name_in_csv(self, tmp_path):
        run_audit_penalty_sweep(
            audit_probabilities=[0.5],
            lie_penalties=[5.0],
            proposer_factory=LyingGreedyProposer,
            responder_factory=_responder_factory,
            n_rounds=5,
            output_dir=tmp_path,
        )
        csv_path = tmp_path / "sweep_summary.csv"
        with csv_path.open(newline="", encoding="utf-8") as fh:
            data = list(csv.DictReader(fh))
        assert data[0]["proposer_class"] == "LyingGreedyProposer"

    def test_multi_seed_csv_row_count(self, tmp_path):
        rows = run_audit_penalty_sweep(
            audit_probabilities=[0.0, 0.5],
            lie_penalties=[0.0],
            proposer_factory=_proposer_factory,
            responder_factory=_responder_factory,
            n_rounds=3,
            seeds=[1, 2],
            output_dir=tmp_path,
        )
        csv_path = tmp_path / "sweep_summary.csv"
        with csv_path.open(newline="", encoding="utf-8") as fh:
            csv_rows = list(csv.DictReader(fh))
        assert len(csv_rows) == len(rows) == 4  # 2 audit_probs × 1 lie_penalty × 2 seeds


# ---------------------------------------------------------------------------
# Public import surface
# ---------------------------------------------------------------------------

class TestPublicImport:
    def test_importable_from_runners(self):
        from ultimatum_arena.runners import run_audit_penalty_sweep, save_sweep_csv  # noqa: F401
