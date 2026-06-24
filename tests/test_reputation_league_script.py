"""Tests for scripts/run_reputation_league_demo.py and probe_reputation_league.py.

No live Ollama/Claude/OpenAI is used: client constructors are patched with a
role-aware fake that returns valid proposer/responder JSON from the prompt role.
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

from scripts.run_reputation_league_demo import (  # noqa: E402
    build_participants,
    main as demo_main,
    parse_args as demo_parse_args,
    resolve_model as demo_resolve_model,
)
from scripts import probe_reputation_league as probe  # noqa: E402


class _RoleAwareFake:
    """Satisfies the LLMClient protocol; role inferred from the prompt."""

    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        if "RESPONDER" in prompt:
            return '{"accept": true}'
        if "review" in prompt.lower():  # gossip prompt
            return '{"text": "ok", "rating": 0.2}'
        return '{"claimed_pie": 80.0, "offer": 32.0, "public_message": "fair"}'


# ---------------------------------------------------------------------------
# demo parse_args
# ---------------------------------------------------------------------------


class TestDemoParseArgs:
    def test_defaults(self) -> None:
        args = demo_parse_args([])
        assert args.provider == "heuristic"
        assert args.agents == 8
        assert args.matches == 40
        assert args.matching == "random"
        assert args.gossip == "off"

    def test_overrides(self) -> None:
        args = demo_parse_args(
            ["--provider", "ollama", "--agents", "4", "--matches", "10", "--matching", "reputation_based"]
        )
        assert args.provider == "ollama"
        assert args.agents == 4
        assert args.matching == "reputation_based"


class TestBuildParticipants:
    def test_heuristic_roster_size_and_no_client(self) -> None:
        args = demo_parse_args(["--provider", "heuristic", "--agents", "6"])
        participants, client, model = build_participants(args)
        assert len(participants) == 6
        assert client is None
        assert model is None
        assert len({p.agent_id for p in participants}) == 6

    def test_llm_roster_shares_client(self) -> None:
        args = demo_parse_args(["--provider", "ollama", "--agents", "5"])
        with patch("scripts.run_reputation_league_demo.OllamaLLMClient", _RoleAwareFake):
            participants, client, model = build_participants(args)
        assert len(participants) == 5
        assert client is not None
        assert model == "gemma3"


class TestModelResolution:
    """P2-1: provider-specific defaults so metadata matches the model actually used."""

    def test_demo_provider_defaults(self) -> None:
        assert demo_resolve_model("heuristic", None) is None
        assert demo_resolve_model("ollama", None) == "gemma3"
        assert demo_resolve_model("claude", None) == "haiku"
        assert demo_resolve_model("openai", None) == "gpt-5.4-mini"

    def test_demo_explicit_model_wins(self) -> None:
        assert demo_resolve_model("claude", "sonnet") == "sonnet"
        assert demo_resolve_model("openai", "gpt-4o") == "gpt-4o"

    def test_probe_provider_defaults(self) -> None:
        assert probe.resolve_model("ollama", None) == "gemma3"
        assert probe.resolve_model("claude", None) == "haiku"
        assert probe.resolve_model("openai", None) == "gpt-5.4-mini"
        assert probe.resolve_model("claude", "opus") == "opus"

    def test_claude_default_recorded_in_profiles(self) -> None:
        # --provider claude without --model must record haiku, not gemma3/None.
        args = demo_parse_args(["--provider", "claude", "--agents", "3"])
        with patch("scripts.run_reputation_league_demo.ClaudeCLIClient", _RoleAwareFake):
            participants, _client, model = build_participants(args)
        assert model == "haiku"
        assert all(p.profile.model == "haiku" for p in participants)


# ---------------------------------------------------------------------------
# demo main (end-to-end, patched clients / heuristic)
# ---------------------------------------------------------------------------


class TestDemoMain:
    def test_heuristic_writes_outputs(self, tmp_path: Path) -> None:
        demo_main(
            [
                "--provider", "heuristic",
                "--agents", "6",
                "--matches", "20",
                "--matching", "reputation_based",
                "--gossip", "deterministic",
                "--output-root", str(tmp_path),
                "--seed", "1",
            ]
        )
        runs = list(tmp_path.iterdir())
        assert len(runs) == 1
        run_dir = runs[0]
        summary = json.loads((run_dir / "league_summary.json").read_text(encoding="utf-8"))
        assert summary["n_matches"] == 20
        assert (run_dir / "leaderboard.csv").exists()

    def test_ollama_main_patched(self, tmp_path: Path) -> None:
        with patch("scripts.run_reputation_league_demo.OllamaLLMClient", _RoleAwareFake):
            demo_main(
                [
                    "--provider", "ollama",
                    "--agents", "4",
                    "--matches", "8",
                    "--gossip", "llm",
                    "--output-root", str(tmp_path),
                    "--seed", "2",
                ]
            )
        run_dir = next(tmp_path.iterdir())
        matches = (run_dir / "matches.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(matches) == 8

    def test_claude_default_model_in_manifest(self, tmp_path: Path) -> None:
        # --provider claude without --model must record haiku in the manifest,
        # matching the model actually called (P2-1).
        with patch("scripts.run_reputation_league_demo.ClaudeCLIClient", _RoleAwareFake):
            demo_main(
                ["--provider", "claude", "--agents", "3", "--matches", "4", "--output-root", str(tmp_path)]
            )
        run_dir = next(tmp_path.iterdir())
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["model"] == "haiku"
        assert "haiku" in manifest["provider_label"]

    def test_llm_gossip_with_heuristic_provider_errors(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            demo_main(
                ["--provider", "heuristic", "--gossip", "llm", "--output-root", str(tmp_path)]
            )


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------


class TestProbe:
    def test_parse_args_defaults(self) -> None:
        args = probe.parse_args([])
        assert args.provider == "ollama"
        assert args.responder_mode == "robust"
        assert args.repeats == 3

    def test_run_probe_with_fake(self) -> None:
        from ultimatum_arena.league.agents import LLMParticipant
        from ultimatum_arena.league.schemas import LeagueAgentProfile

        client = _RoleAwareFake()
        part = LLMParticipant(
            LeagueAgentProfile(agent_id="p", display_name="P", kind="llm"),
            client,
            responder_mode="robust",
        )
        rows = probe.run_probe(part, offer_ratios=[0.05, 0.45], repeats=2)
        assert len(rows) == 2
        for r in rows:
            assert "good_accept_rate" in r
            assert "bad_accept_rate" in r
            assert "reputation_effect" in r
            # P3-2: true paired decision flips, not just an acceptance delta.
            assert "good_only_accepts" in r
            assert "bad_only_accepts" in r
            assert "same_decision" in r
            # All repeats paired (no refusals from the fake client).
            assert r["paired_repeats"] == 2
            assert r["good_only_accepts"] + r["bad_only_accepts"] + r["same_decision"] == 2

    def test_paired_flip_counting(self) -> None:
        # A deterministic client that accepts under the GOOD context (which contains
        # high reputation) and rejects under the BAD context demonstrates a real
        # good-only flip at identical economic terms.
        from ultimatum_arena.league.agents import LLMParticipant
        from ultimatum_arena.league.schemas import LeagueAgentProfile

        class _RepSensitiveFake:
            def generate(self, prompt: str) -> str:
                # The good context renders "public reputation: 92.0"; bad renders "8.0".
                return '{"accept": true}' if "92.0" in prompt else '{"accept": false}'

        part = LLMParticipant(
            LeagueAgentProfile(agent_id="p", display_name="P", kind="llm"),
            _RepSensitiveFake(),
            responder_mode="standard",
        )
        rows = probe.run_probe(part, offer_ratios=[0.05], repeats=3)
        r = rows[0]
        assert r["good_only_accepts"] == 3
        assert r["bad_only_accepts"] == 0
        assert r["reputation_effect"] == 1.0

    def test_probe_main_patched(self, monkeypatch) -> None:
        monkeypatch.setattr(probe, "OllamaLLMClient", _RoleAwareFake)
        # Should run without contacting a live model and write outputs.
        probe.main(["--provider", "ollama", "--offer-ratios", "0.05", "0.45", "--repeats", "1"])
