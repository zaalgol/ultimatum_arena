"""JSONL / JSON persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ultimatum_arena.schemas import RoundResult


def append_result(path: Path | str, result: RoundResult) -> None:
    """Append one RoundResult as a JSON line to *path*."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(result.model_dump_json() + "\n")


def load_results(path: Path | str) -> list[RoundResult]:
    """Load all RoundResult records from a JSONL file."""
    path = Path(path)
    results: list[RoundResult] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                results.append(RoundResult.model_validate_json(line))
    return results


def save_summary(path: Path | str, summary: dict[str, Any]) -> None:
    """Write a summary metrics dict as pretty-printed JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
