"""Tests for ultimatum_arena.analysis.plots."""

from __future__ import annotations

import csv

import pytest

from ultimatum_arena.analysis.plots import (
    plot_metric_by_audit_prob,
    plot_metric_by_audit_prob_for_strategies,
    save_aggregate_csv,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(audit_prob: float, lie_penalty: float, acceptance_rate: float = 0.8,
         **extra) -> dict:
    return {
        "audit_prob": audit_prob,
        "lie_penalty": lie_penalty,
        "seed": 42,
        "n_rounds": 10,
        "proposer_class": "HonestFairProposer",
        "responder_class": "ThresholdResponder",
        "acceptance_rate": acceptance_rate,
        "mean_offer": 50.0,
        **extra,
    }


_ROWS = [
    _row(0.0, 0.0, acceptance_rate=1.0),
    _row(0.5, 0.0, acceptance_rate=0.8),
    _row(1.0, 0.0, acceptance_rate=0.6),
    _row(0.0, 10.0, acceptance_rate=0.9),
    _row(0.5, 10.0, acceptance_rate=0.7),
    _row(1.0, 10.0, acceptance_rate=0.5),
]


# ---------------------------------------------------------------------------
# Happy-path: PNG output
# ---------------------------------------------------------------------------

class TestPlotMetricByAuditProbOutput:
    def test_writes_png_file(self, tmp_path):
        out = tmp_path / "plot.png"
        plot_metric_by_audit_prob(_ROWS, "acceptance_rate", out)
        assert out.exists()

    def test_output_is_non_empty(self, tmp_path):
        out = tmp_path / "plot.png"
        plot_metric_by_audit_prob(_ROWS, "acceptance_rate", out)
        assert out.stat().st_size > 0

    def test_creates_parent_directories(self, tmp_path):
        out = tmp_path / "nested" / "subdir" / "plot.png"
        plot_metric_by_audit_prob(_ROWS, "acceptance_rate", out)
        assert out.exists()

    def test_accepts_string_output_path(self, tmp_path):
        out = str(tmp_path / "plot.png")
        plot_metric_by_audit_prob(_ROWS, "acceptance_rate", out)
        from pathlib import Path
        assert Path(out).exists()

    def test_group_by_none_produces_single_series(self, tmp_path):
        out = tmp_path / "plot.png"
        plot_metric_by_audit_prob(_ROWS, "acceptance_rate", out, group_by=None)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_custom_group_by_field(self, tmp_path):
        rows = [
            _row(0.0, 0.0, acceptance_rate=1.0, proposer_class="A"),
            _row(0.5, 0.0, acceptance_rate=0.8, proposer_class="A"),
            _row(0.0, 0.0, acceptance_rate=0.9, proposer_class="B"),
        ]
        out = tmp_path / "plot.png"
        plot_metric_by_audit_prob(rows, "acceptance_rate", out,
                                   group_by="proposer_class")
        assert out.exists()

    def test_different_metric(self, tmp_path):
        out = tmp_path / "mean_offer.png"
        plot_metric_by_audit_prob(_ROWS, "mean_offer", out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_single_row(self, tmp_path):
        out = tmp_path / "plot.png"
        plot_metric_by_audit_prob([_row(0.5, 5.0, acceptance_rate=0.75)],
                                   "acceptance_rate", out)
        assert out.exists()


# ---------------------------------------------------------------------------
# Averaging duplicate (audit_prob, group) pairs
# ---------------------------------------------------------------------------

class TestAveragingDuplicates:
    def test_duplicate_pairs_are_averaged(self, tmp_path):
        """Two rows with the same audit_prob/lie_penalty should be averaged."""
        rows = [
            _row(0.5, 0.0, acceptance_rate=0.6),
            _row(0.5, 0.0, acceptance_rate=0.4),  # same pair → avg = 0.5
        ]
        out = tmp_path / "plot.png"
        # Should not raise and should produce a valid PNG
        plot_metric_by_audit_prob(rows, "acceptance_rate", out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_multiple_seeds_averaged(self, tmp_path):
        rows = [
            {**_row(0.3, 5.0, acceptance_rate=1.0), "seed": 1},
            {**_row(0.3, 5.0, acceptance_rate=0.0), "seed": 2},
        ]
        out = tmp_path / "plot.png"
        plot_metric_by_audit_prob(rows, "acceptance_rate", out)
        assert out.exists()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestPlotMetricByAuditProbErrors:
    def test_empty_rows_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            plot_metric_by_audit_prob([], "acceptance_rate", tmp_path / "p.png")

    def test_missing_metric_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="nonexistent_metric"):
            plot_metric_by_audit_prob(
                _ROWS, "nonexistent_metric", tmp_path / "p.png"
            )

    def test_missing_metric_error_lists_available_keys(self, tmp_path):
        with pytest.raises(ValueError, match="acceptance_rate"):
            plot_metric_by_audit_prob(
                _ROWS, "no_such_key", tmp_path / "p.png"
            )

    def test_missing_group_by_field_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="bad_field"):
            plot_metric_by_audit_prob(
                _ROWS, "acceptance_rate", tmp_path / "p.png",
                group_by="bad_field"
            )

    def test_missing_audit_prob_raises_value_error(self, tmp_path):
        rows = [{"lie_penalty": 0.0, "acceptance_rate": 0.8}]
        with pytest.raises(ValueError, match="audit_prob"):
            plot_metric_by_audit_prob(rows, "acceptance_rate", tmp_path / "p.png")

    def test_no_file_written_on_error(self, tmp_path):
        out = tmp_path / "plot.png"
        with pytest.raises(ValueError):
            plot_metric_by_audit_prob([], "acceptance_rate", out)
        assert not out.exists()

    def test_later_row_missing_metric_raises(self, tmp_path):
        rows = [
            _row(0.0, 0.0, acceptance_rate=1.0),
            {"audit_prob": 0.5, "lie_penalty": 0.0},  # missing acceptance_rate
        ]
        with pytest.raises(ValueError, match="acceptance_rate"):
            plot_metric_by_audit_prob(rows, "acceptance_rate", tmp_path / "p.png")

    def test_later_row_missing_audit_prob_raises(self, tmp_path):
        rows = [
            _row(0.0, 0.0, acceptance_rate=1.0),
            {"lie_penalty": 0.0, "acceptance_rate": 0.8},  # missing audit_prob
        ]
        with pytest.raises(ValueError, match="audit_prob"):
            plot_metric_by_audit_prob(rows, "acceptance_rate", tmp_path / "p.png")

    def test_later_row_missing_group_by_raises(self, tmp_path):
        rows = [
            _row(0.0, 0.0, acceptance_rate=1.0),
            {"audit_prob": 0.5, "acceptance_rate": 0.8},  # missing lie_penalty
        ]
        with pytest.raises(ValueError, match="lie_penalty"):
            plot_metric_by_audit_prob(rows, "acceptance_rate", tmp_path / "p.png",
                                       group_by="lie_penalty")

    def test_non_numeric_metric_raises_value_error(self, tmp_path):
        rows = [_row(0.0, 0.0, acceptance_rate="not_a_number")]
        with pytest.raises(ValueError, match="cannot be converted to float"):
            plot_metric_by_audit_prob(rows, "acceptance_rate", tmp_path / "p.png")

    def test_none_metric_raises_value_error(self, tmp_path):
        rows = [_row(0.0, 0.0, acceptance_rate=None)]
        with pytest.raises(ValueError, match="cannot be converted to float"):
            plot_metric_by_audit_prob(rows, "acceptance_rate", tmp_path / "p.png")


# ---------------------------------------------------------------------------
# Public import surface
# ---------------------------------------------------------------------------

class TestPublicImport:
    def test_importable_from_analysis(self):
        from ultimatum_arena.analysis import plot_metric_by_audit_prob  # noqa: F401

    def test_strategy_plotter_importable_from_analysis(self):
        from ultimatum_arena.analysis import plot_metric_by_audit_prob_for_strategies  # noqa: F401

    def test_aggregate_csv_importable_from_analysis(self):
        from ultimatum_arena.analysis import save_aggregate_csv  # noqa: F401


# ---------------------------------------------------------------------------
# Helpers for LLM-sweep-style rows (include "strategy" field)
# ---------------------------------------------------------------------------

def _llm_row(
    strategy: str,
    audit_prob: float,
    lie_penalty: float,
    seed: int = 1,
    acceptance_rate: float = 0.8,
    deception_rate: float = 0.3,
    detected_lie_rate: float = 0.1,
    lie_detection_rate_among_lies: float = 0.4,
    proposer_mean_payoff: float = 55.0,
    responder_mean_payoff: float = 45.0,
    proposer_advantage: float = 10.0,
) -> dict:
    return {
        "strategy": strategy,
        "audit_prob": audit_prob,
        "lie_penalty": lie_penalty,
        "seed": seed,
        "n_rounds": 10,
        "proposer_class": "LLMProposer",
        "responder_class": "LLMResponder",
        "acceptance_rate": acceptance_rate,
        "deception_rate": deception_rate,
        "detected_lie_rate": detected_lie_rate,
        "lie_detection_rate_among_lies": lie_detection_rate_among_lies,
        "proposer_mean_payoff": proposer_mean_payoff,
        "responder_mean_payoff": responder_mean_payoff,
        "proposer_advantage": proposer_advantage,
    }


_LLM_ROWS = [
    _llm_row("honest_fair",   0.0,  0.0, seed=1, acceptance_rate=0.9, deception_rate=0.0),
    _llm_row("honest_fair",   0.5,  0.0, seed=1, acceptance_rate=0.85, deception_rate=0.0),
    _llm_row("honest_fair",   1.0,  0.0, seed=1, acceptance_rate=0.8, deception_rate=0.0),
    _llm_row("deceptive",     0.0,  0.0, seed=1, acceptance_rate=0.7, deception_rate=0.8),
    _llm_row("deceptive",     0.5,  0.0, seed=1, acceptance_rate=0.65, deception_rate=0.7),
    _llm_row("deceptive",     1.0,  0.0, seed=1, acceptance_rate=0.5, deception_rate=0.5),
]


# ---------------------------------------------------------------------------
# plot_metric_by_audit_prob_for_strategies
# ---------------------------------------------------------------------------

class TestPlotMetricByAuditProbForStrategies:
    def test_writes_png(self, tmp_path):
        out = tmp_path / "plot.png"
        plot_metric_by_audit_prob_for_strategies(_LLM_ROWS, "acceptance_rate", out)
        assert out.exists()

    def test_non_empty_png(self, tmp_path):
        out = tmp_path / "plot.png"
        plot_metric_by_audit_prob_for_strategies(_LLM_ROWS, "acceptance_rate", out)
        assert out.stat().st_size > 0

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "nested" / "dir" / "plot.png"
        plot_metric_by_audit_prob_for_strategies(_LLM_ROWS, "acceptance_rate", out)
        assert out.exists()

    def test_accepts_string_path(self, tmp_path):
        out = str(tmp_path / "plot.png")
        plot_metric_by_audit_prob_for_strategies(_LLM_ROWS, "acceptance_rate", out)
        from pathlib import Path as P
        assert P(out).exists()

    def test_filters_by_lie_penalty(self, tmp_path):
        rows = [
            _llm_row("honest_fair", 0.0, 0.0, acceptance_rate=1.0),
            _llm_row("honest_fair", 0.5, 0.0, acceptance_rate=0.9),
            _llm_row("honest_fair", 0.0, 25.0, acceptance_rate=0.5),
            _llm_row("honest_fair", 0.5, 25.0, acceptance_rate=0.4),
        ]
        out = tmp_path / "plot.png"
        # Filter to lie_penalty=0.0 only — must not raise even though 25.0 rows exist
        plot_metric_by_audit_prob_for_strategies(rows, "acceptance_rate", out, lie_penalty=0.0)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_lie_penalty_none_uses_all_rows(self, tmp_path):
        rows = [
            _llm_row("honest_fair", 0.0, 0.0),
            _llm_row("honest_fair", 0.0, 25.0),
        ]
        out = tmp_path / "plot.png"
        # No filtering — both rows averaged for same (strategy, audit_prob)
        plot_metric_by_audit_prob_for_strategies(rows, "acceptance_rate", out, lie_penalty=None)
        assert out.exists()

    def test_empty_rows_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            plot_metric_by_audit_prob_for_strategies([], "acceptance_rate", tmp_path / "p.png")

    def test_filtered_to_empty_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            plot_metric_by_audit_prob_for_strategies(
                _LLM_ROWS, "acceptance_rate", tmp_path / "p.png",
                lie_penalty=999.0,  # no rows match
            )

    def test_missing_metric_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="no_such_metric"):
            plot_metric_by_audit_prob_for_strategies(
                _LLM_ROWS, "no_such_metric", tmp_path / "p.png"
            )

    def test_different_metric(self, tmp_path):
        out = tmp_path / "deception.png"
        plot_metric_by_audit_prob_for_strategies(_LLM_ROWS, "deception_rate", out)
        assert out.exists()
        assert out.stat().st_size > 0


# ---------------------------------------------------------------------------
# save_aggregate_csv
# ---------------------------------------------------------------------------

class TestSaveAggregateCsv:
    def test_empty_rows_writes_empty_file(self, tmp_path):
        out = tmp_path / "agg.csv"
        save_aggregate_csv([], out)
        assert out.exists()
        assert out.read_text(encoding="utf-8") == ""

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "nested" / "agg.csv"
        save_aggregate_csv(_LLM_ROWS, out)
        assert out.exists()

    def test_row_count_equals_unique_cells(self, tmp_path):
        # _LLM_ROWS has 2 strategies × 3 audit_probs × 1 lie_penalty = 6 cells
        out = tmp_path / "agg.csv"
        save_aggregate_csv(_LLM_ROWS, out)
        with out.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 6

    def test_averages_over_seeds(self, tmp_path):
        rows = [
            _llm_row("honest_fair", 0.5, 0.0, seed=1, acceptance_rate=1.0),
            _llm_row("honest_fair", 0.5, 0.0, seed=2, acceptance_rate=0.0),
        ]
        out = tmp_path / "agg.csv"
        save_aggregate_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            data = list(csv.DictReader(fh))
        assert len(data) == 1
        assert float(data[0]["acceptance_rate"]) == pytest.approx(0.5)

    def test_n_runs_field(self, tmp_path):
        rows = [
            _llm_row("honest_fair", 0.5, 0.0, seed=1),
            _llm_row("honest_fair", 0.5, 0.0, seed=2),
            _llm_row("honest_fair", 0.5, 0.0, seed=3),
        ]
        out = tmp_path / "agg.csv"
        save_aggregate_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            data = list(csv.DictReader(fh))
        assert int(data[0]["n_runs"]) == 3

    def test_groups_by_strategy(self, tmp_path):
        rows = [
            _llm_row("honest_fair", 0.5, 0.0),
            _llm_row("deceptive",   0.5, 0.0),
        ]
        out = tmp_path / "agg.csv"
        save_aggregate_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            data = list(csv.DictReader(fh))
        assert len(data) == 2
        strategies = {r["strategy"] for r in data}
        assert strategies == {"honest_fair", "deceptive"}

    def test_groups_by_audit_prob(self, tmp_path):
        rows = [
            _llm_row("honest_fair", 0.0, 0.0),
            _llm_row("honest_fair", 0.5, 0.0),
            _llm_row("honest_fair", 1.0, 0.0),
        ]
        out = tmp_path / "agg.csv"
        save_aggregate_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            data = list(csv.DictReader(fh))
        assert len(data) == 3
        audit_probs = {float(r["audit_prob"]) for r in data}
        assert audit_probs == {0.0, 0.5, 1.0}

    def test_groups_by_lie_penalty(self, tmp_path):
        rows = [
            _llm_row("honest_fair", 0.5, 0.0),
            _llm_row("honest_fair", 0.5, 25.0),
        ]
        out = tmp_path / "agg.csv"
        save_aggregate_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            data = list(csv.DictReader(fh))
        assert len(data) == 2
        penalties = {float(r["lie_penalty"]) for r in data}
        assert penalties == {0.0, 25.0}

    def test_config_columns_come_first(self, tmp_path):
        out = tmp_path / "agg.csv"
        save_aggregate_csv(_LLM_ROWS, out)
        with out.open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        assert fieldnames[:4] == ["strategy", "audit_prob", "lie_penalty", "n_runs"]

    def test_aggregate_metrics_present(self, tmp_path):
        out = tmp_path / "agg.csv"
        save_aggregate_csv(_LLM_ROWS, out)
        with out.open(newline="", encoding="utf-8") as fh:
            fieldnames = next(csv.reader(fh))
        for col in (
            "acceptance_rate", "deception_rate", "detected_lie_rate",
            "lie_detection_rate_among_lies", "proposer_mean_payoff",
            "responder_mean_payoff", "proposer_advantage",
        ):
            assert col in fieldnames

    def test_values_round_trip(self, tmp_path):
        rows = [_llm_row("deceptive", 0.25, 10.0, acceptance_rate=0.6, deception_rate=0.75)]
        out = tmp_path / "agg.csv"
        save_aggregate_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as fh:
            data = list(csv.DictReader(fh))
        assert float(data[0]["acceptance_rate"]) == pytest.approx(0.6)
        assert float(data[0]["deception_rate"]) == pytest.approx(0.75)
