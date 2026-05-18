"""Tests for ultimatum_arena.analysis.sweep_summary."""

from __future__ import annotations

import math

import pytest

from ultimatum_arena.analysis.sweep_summary import (
    summarize_adaptive_strategies,
    summarize_strategy_by_audit_risk,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(
    strategy: str = "risk_aware",
    audit_prob: float = 0.0,
    lie_penalty: float = 25.0,
    seed: int = 1,
    *,
    deception_rate: float = 0.5,
    proposer_mean_payoff: float = 30.0,
    proposer_advantage: float = 10.0,
    lie_detection_rate_among_lies: float = 0.2,
) -> dict:
    return {
        "strategy": strategy,
        "audit_prob": audit_prob,
        "lie_penalty": lie_penalty,
        "seed": seed,
        "deception_rate": deception_rate,
        "proposer_mean_payoff": proposer_mean_payoff,
        "proposer_advantage": proposer_advantage,
        "lie_detection_rate_among_lies": lie_detection_rate_among_lies,
    }


# ---------------------------------------------------------------------------
# Basic grouping and sorting
# ---------------------------------------------------------------------------

class TestGroupingByAuditProb:
    def test_groups_by_audit_prob(self):
        rows = [
            _row(audit_prob=0.0),
            _row(audit_prob=0.5),
            _row(audit_prob=1.0),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert len(result) == 3

    def test_sorted_numerically(self):
        rows = [
            _row(audit_prob=1.0),
            _row(audit_prob=0.0),
            _row(audit_prob=0.5),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        probs = [r["audit_prob"] for r in result]
        assert probs == sorted(probs)

    def test_returns_strategy_field(self):
        rows = [_row(audit_prob=0.25)]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert result[0]["strategy"] == "risk_aware"

    def test_returns_n_runs(self):
        rows = [_row(audit_prob=0.0, seed=1), _row(audit_prob=0.0, seed=2)]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert result[0]["n_runs"] == 2

    def test_returns_required_metric_keys(self):
        rows = [_row(audit_prob=0.25)]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        for key in (
            "deception_rate",
            "proposer_mean_payoff",
            "proposer_advantage",
            "lie_detection_rate_among_lies",
        ):
            assert key in result[0]


# ---------------------------------------------------------------------------
# Averaging across seeds
# ---------------------------------------------------------------------------

class TestAveragingAcrossSeeds:
    def test_averages_deception_rate_across_seeds(self):
        rows = [
            _row(audit_prob=0.5, seed=1, deception_rate=0.2),
            _row(audit_prob=0.5, seed=2, deception_rate=0.4),
            _row(audit_prob=0.5, seed=3, deception_rate=0.6),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert result[0]["deception_rate"] == pytest.approx(0.4)

    def test_averages_proposer_payoff_across_seeds(self):
        rows = [
            _row(audit_prob=0.0, seed=1, proposer_mean_payoff=10.0),
            _row(audit_prob=0.0, seed=2, proposer_mean_payoff=20.0),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert result[0]["proposer_mean_payoff"] == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# Lie penalty filter
# ---------------------------------------------------------------------------

class TestLiePenaltyFilter:
    def test_filters_by_lie_penalty(self):
        rows = [
            _row(audit_prob=0.5, lie_penalty=0.0, deception_rate=0.8),
            _row(audit_prob=0.5, lie_penalty=50.0, deception_rate=0.2),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware", lie_penalty=50.0)
        assert len(result) == 1
        assert result[0]["deception_rate"] == pytest.approx(0.2)

    def test_no_filter_includes_all_penalties(self):
        rows = [
            _row(audit_prob=0.5, lie_penalty=0.0),
            _row(audit_prob=0.5, lie_penalty=25.0),
            _row(audit_prob=0.5, lie_penalty=50.0),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert result[0]["n_runs"] == 3


# ---------------------------------------------------------------------------
# Strategy filter
# ---------------------------------------------------------------------------

class TestStrategyFilter:
    def test_excludes_other_strategies(self):
        rows = [
            _row(strategy="risk_aware", audit_prob=0.0),
            _row(strategy="honest_fair", audit_prob=0.0),
            _row(strategy="deceptive", audit_prob=0.0),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert all(r["strategy"] == "risk_aware" for r in result)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Empty / no-match
# ---------------------------------------------------------------------------

class TestEmptyMatch:
    def test_raises_value_error_when_no_rows_match_strategy(self):
        rows = [_row(strategy="honest_fair")]
        with pytest.raises(ValueError):
            summarize_strategy_by_audit_risk(rows, "risk_aware")

    def test_raises_value_error_when_no_rows_match_penalty(self):
        rows = [_row(strategy="risk_aware", lie_penalty=25.0)]
        with pytest.raises(ValueError):
            summarize_strategy_by_audit_risk(rows, "risk_aware", lie_penalty=99.0)

    def test_raises_value_error_on_empty_input(self):
        with pytest.raises(ValueError):
            summarize_strategy_by_audit_risk([], "risk_aware")


# ---------------------------------------------------------------------------
# CSV-loaded string rows (all numeric fields are strings)
# ---------------------------------------------------------------------------

def _csv_row(
    strategy: str = "risk_aware",
    audit_prob: str = "0.0",
    lie_penalty: str = "25.0",
    deception_rate: str = "0.5",
    proposer_mean_payoff: str = "30.0",
    proposer_advantage: str = "10.0",
    lie_detection_rate_among_lies: str = "0.2",
) -> dict:
    """Return a row where all numeric values are strings, as from csv.DictReader."""
    return {
        "strategy": strategy,
        "audit_prob": audit_prob,
        "lie_penalty": lie_penalty,
        "deception_rate": deception_rate,
        "proposer_mean_payoff": proposer_mean_payoff,
        "proposer_advantage": proposer_advantage,
        "lie_detection_rate_among_lies": lie_detection_rate_among_lies,
    }


class TestCsvStringRows:
    def test_string_audit_prob_groups_correctly(self):
        rows = [
            _csv_row(audit_prob="0.0"),
            _csv_row(audit_prob="0.5"),
            _csv_row(audit_prob="1.0"),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert len(result) == 3

    def test_string_audit_prob_sorts_numerically(self):
        rows = [
            _csv_row(audit_prob="1.0"),
            _csv_row(audit_prob="0.0"),
            _csv_row(audit_prob="0.25"),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        probs = [r["audit_prob"] for r in result]
        assert probs == sorted(probs)

    def test_string_metric_values_averaged(self):
        rows = [
            _csv_row(audit_prob="0.5", deception_rate="0.2"),
            _csv_row(audit_prob="0.5", deception_rate="0.4"),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert result[0]["deception_rate"] == pytest.approx(0.3)

    def test_string_lie_penalty_filter(self):
        rows = [
            _csv_row(audit_prob="0.5", lie_penalty="0.0", deception_rate="0.9"),
            _csv_row(audit_prob="0.5", lie_penalty="25.0", deception_rate="0.2"),
        ]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware", lie_penalty=25.0)
        assert len(result) == 1
        assert result[0]["deception_rate"] == pytest.approx(0.2)

    def test_audit_prob_in_output_is_float(self):
        rows = [_csv_row(audit_prob="0.25")]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert isinstance(result[0]["audit_prob"], float)


# ---------------------------------------------------------------------------
# NaN handling for missing metric keys
# ---------------------------------------------------------------------------

class TestMissingMetrics:
    def test_nan_for_missing_metric_key(self):
        rows = [{"strategy": "risk_aware", "audit_prob": 0.0, "lie_penalty": 0.0}]
        result = summarize_strategy_by_audit_risk(rows, "risk_aware")
        assert math.isnan(result[0]["deception_rate"])


# ---------------------------------------------------------------------------
# summarize_adaptive_strategies
# ---------------------------------------------------------------------------

def _multi_row(strategy: str, audit_prob: float, deception_rate: float = 0.5) -> dict:
    return {
        "strategy": strategy,
        "audit_prob": audit_prob,
        "lie_penalty": 25.0,
        "deception_rate": deception_rate,
        "proposer_mean_payoff": 30.0,
        "proposer_advantage": 10.0,
        "lie_detection_rate_among_lies": 0.2,
    }


class TestSummarizeAdaptiveStrategies:
    def test_default_strategies_are_risk_aware_and_expected_value(self):
        rows = [
            _multi_row("risk_aware", 0.0),
            _multi_row("expected_value", 0.0),
        ]
        result = summarize_adaptive_strategies(rows)
        strategies_seen = {r["strategy"] for r in result}
        assert strategies_seen == {"risk_aware", "expected_value"}

    def test_custom_strategies_list(self):
        rows = [
            _multi_row("honest_fair", 0.0),
            _multi_row("deceptive", 0.0),
        ]
        result = summarize_adaptive_strategies(rows, ["honest_fair", "deceptive"])
        assert len(result) == 2

    def test_skips_missing_strategy_silently(self):
        rows = [_multi_row("risk_aware", 0.0)]
        result = summarize_adaptive_strategies(rows, ["risk_aware", "expected_value"])
        # expected_value not in rows; only risk_aware rows returned
        assert all(r["strategy"] == "risk_aware" for r in result)

    def test_returns_empty_when_no_strategies_match(self):
        rows = [_multi_row("honest_fair", 0.0)]
        result = summarize_adaptive_strategies(rows, ["risk_aware", "expected_value"])
        assert result == []

    def test_results_ordered_by_strategy_then_audit_prob(self):
        rows = [
            _multi_row("risk_aware", 1.0),
            _multi_row("risk_aware", 0.0),
            _multi_row("expected_value", 0.5),
            _multi_row("expected_value", 0.0),
        ]
        result = summarize_adaptive_strategies(rows, ["risk_aware", "expected_value"])
        risk_rows = [r for r in result if r["strategy"] == "risk_aware"]
        ev_rows = [r for r in result if r["strategy"] == "expected_value"]
        # risk_aware rows come first (list order), each sorted by audit_prob
        assert result.index(risk_rows[0]) < result.index(ev_rows[0])
        assert risk_rows[0]["audit_prob"] < risk_rows[1]["audit_prob"]
        assert ev_rows[0]["audit_prob"] < ev_rows[1]["audit_prob"]

    def test_lie_penalty_filter_forwarded(self):
        rows = [
            _multi_row("risk_aware", 0.5) | {"lie_penalty": 0.0, "deception_rate": 0.9},
            _multi_row("risk_aware", 0.5) | {"lie_penalty": 25.0, "deception_rate": 0.2},
        ]
        result = summarize_adaptive_strategies(rows, ["risk_aware"], lie_penalty=25.0)
        assert len(result) == 1
        assert result[0]["deception_rate"] == pytest.approx(0.2)

    def test_works_with_csv_string_rows(self):
        rows = [
            _csv_row(strategy="expected_value", audit_prob="0.0"),
            _csv_row(strategy="risk_aware", audit_prob="0.0"),
        ]
        result = summarize_adaptive_strategies(rows)
        assert len(result) == 2

    def test_malformed_numeric_field_propagates_not_silenced(self):
        """A matching strategy with a bad numeric field must raise, not return []."""
        rows = [
            {
                "strategy": "expected_value",
                "audit_prob": "bad",   # malformed — not a valid float
                "lie_penalty": "25.0",
                "deception_rate": "0.5",
                "proposer_mean_payoff": "30.0",
                "proposer_advantage": "10.0",
                "lie_detection_rate_among_lies": "0.2",
            }
        ]
        with pytest.raises((ValueError, TypeError)):
            summarize_adaptive_strategies(rows, ["expected_value"])


# ---------------------------------------------------------------------------
# Public import
# ---------------------------------------------------------------------------

class TestPublicImport:
    def test_importable_from_analysis(self):
        from ultimatum_arena.analysis import summarize_strategy_by_audit_risk  # noqa: F401

    def test_adaptive_helper_importable_from_analysis(self):
        from ultimatum_arena.analysis import summarize_adaptive_strategies  # noqa: F401
