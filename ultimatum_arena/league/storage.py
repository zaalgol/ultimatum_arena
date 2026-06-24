"""Persistence helpers for league seasons.

Writes a timestamped output tree::

    outputs/reputation_league/YYYYMMDD_HHMMSS/
      manifest.json
      matches.jsonl
      match_failures.jsonl        (only if any refusals/parse failures occurred)
      final_agent_states.json
      public_reputation_history.csv
      gossip.jsonl
      league_summary.json
      leaderboard.csv

All artifacts are JSON/CSV/JSONL so findings derive from files, not terminal
scrollback. ``outputs/`` is git-ignored.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Sequence

from ultimatum_arena.league.schemas import (
    GossipRecord,
    LeagueAgentState,
    LeagueMatchRecord,
)


def _write_jsonl(path: Path, models: Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for m in models:
            fh.write(m.model_dump_json() + "\n")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def write_reputation_history(path: Path, history: Sequence[dict[str, Any]]) -> None:
    """Write the reputation-after-each-match snapshots as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["match_index", "match_id", "agent_id", "role", "reputation_after"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in history:
            writer.writerow({k: row.get(k) for k in fieldnames})


def write_leaderboard(path: Path, leaderboard: Sequence[dict[str, Any]]) -> None:
    """Write the leaderboard rows (from league metrics) as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not leaderboard:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(leaderboard[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in leaderboard:
            writer.writerow(row)


def write_league_outputs(
    output_dir: Path | str,
    *,
    manifest: dict[str, Any],
    records: Sequence[LeagueMatchRecord],
    failures: Sequence[LeagueMatchRecord],
    final_states: Sequence[LeagueAgentState],
    gossip_records: Sequence[GossipRecord],
    reputation_history: Sequence[dict[str, Any]],
    summary: dict[str, Any],
) -> Path:
    """Write the full league output tree and return the output directory path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_json(output_dir / "manifest.json", manifest)
    _write_jsonl(output_dir / "matches.jsonl", records)
    if failures:
        _write_jsonl(output_dir / "match_failures.jsonl", failures)
    _write_json(
        output_dir / "final_agent_states.json",
        [s.model_dump() for s in final_states],
    )
    write_reputation_history(output_dir / "public_reputation_history.csv", reputation_history)
    _write_jsonl(output_dir / "gossip.jsonl", gossip_records)
    _write_json(output_dir / "league_summary.json", summary)
    write_leaderboard(output_dir / "leaderboard.csv", summary.get("leaderboard", []))

    return output_dir
