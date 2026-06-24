"""Private per-agent memory of opponents.

Each agent keeps a small, capped list of deterministic summaries about the
opponents it has met. Memory is built from **publicly available** information:
an audit makes ``true_pie`` public for that match, so an observer only learns
whether an opponent claimed truthfully (and the true offer ratio) when the
match was audited. Without an audit, the truth stays hidden.

Memory is private to the observer and never exposes other agents' memories.
All summaries are deterministic text generated from the match record, so they
are transparent and reproducible.
"""

from __future__ import annotations

from ultimatum_arena.league.schemas import (
    LeagueMatchRecord,
    MemoryConfig,
    PrivateMemoryEntry,
)


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def _summarize_proposer_target(
    name: str, record: LeagueMatchRecord
) -> tuple[str, float | None, float | None, bool | None]:
    """Summary for when the *target* played proposer (observer was responder).

    Returns ``(summary, offer_ratio_claimed, offer_ratio_true, claimed_truthfully)``.
    ``offer_ratio_true`` / ``claimed_truthfully`` are only known on audited matches.
    """
    ratio_claimed = (record.offer / record.claimed_pie) if record.claimed_pie > 0 else None
    decision = "accepted by you" if record.accepted else "rejected by you"

    if record.audit_occurred:
        ratio_true = (record.offer / record.true_pie) if record.true_pie > 0 else None
        truthful = record.claimed_pie == record.true_pie
        if record.lie_detected:
            summary = (
                f"As proposer, {name} underclaimed the pie (claimed "
                f"{record.claimed_pie:.1f} vs true {record.true_pie:.1f}) and was caught "
                f"by audit; offered {record.offer:.1f} "
                f"({_pct(ratio_true) if ratio_true is not None else 'n/a'} of true pie); "
                f"offer {decision}."
            )
        else:
            summary = (
                f"As proposer, {name} reported truthfully (claimed "
                f"{record.claimed_pie:.1f}); offered {record.offer:.1f} "
                f"({_pct(ratio_true) if ratio_true is not None else 'n/a'} of true pie); "
                f"offer {decision}."
            )
        return summary, ratio_claimed, ratio_true, truthful

    summary = (
        f"As proposer, {name} claimed {record.claimed_pie:.1f} and offered "
        f"{record.offer:.1f} "
        f"({_pct(ratio_claimed) if ratio_claimed is not None else 'n/a'} of claimed pie); "
        f"not audited, so true pie unknown."
    )
    return summary, ratio_claimed, None, None


def _summarize_responder_target(
    name: str, record: LeagueMatchRecord
) -> tuple[str, float | None]:
    """Summary for when the *target* played responder (observer was proposer)."""
    ratio_claimed = (record.offer / record.claimed_pie) if record.claimed_pie > 0 else None
    decision = "accepted" if record.accepted else "rejected"
    summary = (
        f"As responder, {name} {decision} an offer of {record.offer:.1f} "
        f"({_pct(ratio_claimed) if ratio_claimed is not None else 'n/a'} of claimed pie)."
    )
    return summary, ratio_claimed


def build_memory_entry(
    *,
    observer_id: str,
    target_id: str,
    target_name: str,
    target_role: str,
    record: LeagueMatchRecord,
) -> PrivateMemoryEntry:
    """Build one deterministic memory entry the observer keeps about the target."""
    if target_role == "proposer":
        summary, ratio_claimed, ratio_true, truthful = _summarize_proposer_target(
            target_name, record
        )
        public_message = record.public_message
    elif target_role == "responder":
        summary, ratio_claimed = _summarize_responder_target(target_name, record)
        ratio_true = None
        truthful = None
        public_message = ""
    else:  # pragma: no cover - defensive
        raise ValueError(f"Unknown target_role {target_role!r}")

    return PrivateMemoryEntry(
        observer_id=observer_id,
        target_id=target_id,
        match_id=record.match_id,
        season_index=record.season_index,
        target_role=target_role,
        accepted=record.accepted,
        target_offer_ratio_claimed=ratio_claimed,
        target_offer_ratio_true=ratio_true,
        target_claimed_truthfully=truthful,
        target_public_message=public_message,
        summary=summary,
    )


class PrivateMemoryStore:
    """In-memory store of per-observer, per-target memory entries.

    Layout: ``{observer_id: {target_id: [entries oldest..newest]}}``. Retrieval
    returns only memories the observer holds about a specific opponent, capped at
    the configured per-opponent limit.
    """

    def __init__(self, config: MemoryConfig | None = None) -> None:
        self.config = config or MemoryConfig()
        self._store: dict[str, dict[str, list[PrivateMemoryEntry]]] = {}

    def add(self, entry: PrivateMemoryEntry) -> None:
        if not self.config.enabled:
            return
        by_target = self._store.setdefault(entry.observer_id, {})
        entries = by_target.setdefault(entry.target_id, [])
        entries.append(entry)
        # Keep memory bounded: retain only the most recent per-opponent entries.
        limit = self.config.per_opponent_limit
        if limit >= 0 and len(entries) > limit:
            del entries[: len(entries) - limit]

    def recent_about(
        self, observer_id: str, target_id: str, limit: int | None = None
    ) -> list[PrivateMemoryEntry]:
        """Return the observer's most recent memories about ``target_id``."""
        if not self.config.enabled:
            return []
        entries = self._store.get(observer_id, {}).get(target_id, [])
        if limit is None:
            limit = self.config.per_opponent_limit
        if limit <= 0:
            return []
        return entries[-limit:]

    def record_match(
        self,
        record: LeagueMatchRecord,
        *,
        proposer_name: str,
        responder_name: str,
    ) -> None:
        """Record both participants' private memories of one match."""
        if not self.config.enabled:
            return
        # Responder remembers the proposer (target played proposer).
        self.add(
            build_memory_entry(
                observer_id=record.responder_id,
                target_id=record.proposer_id,
                target_name=proposer_name,
                target_role="proposer",
                record=record,
            )
        )
        # Proposer remembers the responder (target played responder).
        self.add(
            build_memory_entry(
                observer_id=record.proposer_id,
                target_id=record.responder_id,
                target_name=responder_name,
                target_role="responder",
                record=record,
            )
        )
