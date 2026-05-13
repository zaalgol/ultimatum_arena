"""Tests for ultimatum_arena.analysis.plots."""

from __future__ import annotations

import pytest

from ultimatum_arena.analysis.plots import plot_metric_by_audit_prob


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
