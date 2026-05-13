"""Integration tests for run_experiment."""

import json
import tempfile
from pathlib import Path

import pytest

from ultimatum_arena.agents import HonestFairProposer, ThresholdResponder
from ultimatum_arena.envs.hidden_pie_audit import HiddenPieAuditEnv
from ultimatum_arena.runners.basic import run_experiment
from ultimatum_arena.storage.jsonl import load_results


class TestRunExperiment:
    def test_returns_correct_number_of_results(self) -> None:
        env = HiddenPieAuditEnv(rng_seed=42)
        results, _ = run_experiment(HonestFairProposer(), ThresholdResponder(), env, n_rounds=10)
        assert len(results) == 10

    def test_summary_has_expected_keys(self) -> None:
        env = HiddenPieAuditEnv(rng_seed=42)
        _, summary = run_experiment(HonestFairProposer(), ThresholdResponder(), env, n_rounds=5)
        for key in (
            "acceptance_rate",
            "deception_rate",
            "mean_offer",
            "detected_lie_rate",
            "proposer_total_payoff",
            "responder_total_payoff",
        ):
            assert key in summary

    def test_saves_jsonl_and_summary(self) -> None:
        env = HiddenPieAuditEnv(rng_seed=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            run_experiment(
                HonestFairProposer(),
                ThresholdResponder(),
                env,
                n_rounds=7,
                output_dir=tmpdir,
                experiment_name="test_run",
            )
            jsonl_path = Path(tmpdir) / "test_run.jsonl"
            summary_path = Path(tmpdir) / "test_run_summary.json"
            assert jsonl_path.exists()
            assert summary_path.exists()

            loaded = load_results(jsonl_path)
            assert len(loaded) == 7

            with summary_path.open() as f:
                s = json.load(f)
            assert s["n_rounds"] == 7

    def test_round_indices_are_sequential(self) -> None:
        env = HiddenPieAuditEnv(rng_seed=1)
        results, _ = run_experiment(HonestFairProposer(), ThresholdResponder(), env, n_rounds=5)
        assert [r.round_index for r in results] == list(range(5))

    def test_honest_fair_zero_deception_rate(self) -> None:
        env = HiddenPieAuditEnv(audit_prob=1.0, rng_seed=7)
        _, summary = run_experiment(HonestFairProposer(), ThresholdResponder(), env, n_rounds=20)
        assert summary["deception_rate"] == pytest.approx(0.0)
        assert summary["detected_lie_rate"] == pytest.approx(0.0)
