"""Canonical declared source-use assessments for review artifacts."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .config import SourcePlan, SourceRecord, SourceUse, Track, load_plan_bytes

COMPLETE_STATUS = (
    "DECLARED SOURCE-USE RECORD - SOURCE ORIGIN, CLEARANCE, CONSENT, LICENSING, "
    "ACCURACY, AND RELEASE-READINESS STATUS UNVERIFIED"
)
INCOMPLETE_STATUS = (
    "INCOMPLETE DECLARED SOURCE-USE RECORD - ONE OR MORE DECLARED SOURCE RECORDS "
    "ARE MARKED NEEDS_REVIEW OR UNRESOLVED; SOURCE ORIGIN, CLEARANCE, CONSENT, "
    "LICENSING, ACCURACY, AND RELEASE-READINESS STATUS UNVERIFIED"
)
REVIEW_REQUIRED_STATES = frozenset({"needs_review", "unresolved"})


@dataclass(frozen=True)
class TrackUse:
    track_id: str
    track_number: int
    track_title: str
    usage_note: str


@dataclass(frozen=True)
class SourceAssessment:
    identifier: str
    description: str
    source_kind: str
    review_state: str
    review_next_step: str
    notes: str
    uses: tuple[TrackUse, ...]


@dataclass(frozen=True)
class SourceLedgerAssessment:
    plan: SourcePlan
    plan_sha256: str
    status: str
    sources: tuple[SourceAssessment, ...]

    @property
    def review_required_count(self) -> int:
        return sum(
            source.review_state in REVIEW_REQUIRED_STATES for source in self.sources
        )


def assess(plan_path: Path) -> SourceLedgerAssessment:
    """Build a canonical review view without inspecting audio or external evidence."""
    plan_bytes = plan_path.read_bytes()
    plan = load_plan_bytes(plan_bytes)
    tracks = {track.identifier.casefold(): track for track in plan.tracks}
    uses_by_source = _uses_by_source(plan.uses, tracks)
    sources = tuple(
        _assess_source(source, uses_by_source.get(source.identifier.casefold(), ()))
        for source in sorted(
            plan.sources, key=lambda item: (item.identifier.casefold(), item.identifier)
        )
    )
    review_required = any(
        source.review_state in REVIEW_REQUIRED_STATES for source in sources
    )
    return SourceLedgerAssessment(
        plan=plan,
        plan_sha256=hashlib.sha256(plan_bytes).hexdigest(),
        status=INCOMPLETE_STATUS if review_required else COMPLETE_STATUS,
        sources=sources,
    )


def _uses_by_source(
    uses: tuple[SourceUse, ...], tracks: dict[str, Track]
) -> dict[str, tuple[TrackUse, ...]]:
    grouped: dict[str, list[TrackUse]] = {}
    for source_use in uses:
        track = tracks[source_use.track_id.casefold()]
        grouped.setdefault(source_use.source_id.casefold(), []).append(
            TrackUse(
                track_id=track.identifier,
                track_number=track.number,
                track_title=track.title,
                usage_note=source_use.usage_note,
            )
        )
    return {
        source_id: tuple(
            sorted(
                source_uses,
                key=lambda item: (
                    item.track_number,
                    item.track_id.casefold(),
                    item.track_id,
                ),
            )
        )
        for source_id, source_uses in grouped.items()
    }


def _assess_source(
    source: SourceRecord, uses: tuple[TrackUse, ...]
) -> SourceAssessment:
    return SourceAssessment(
        identifier=source.identifier,
        description=source.description,
        source_kind=source.source_kind,
        review_state=source.review_state,
        review_next_step=source.review_next_step,
        notes=source.notes,
        uses=uses,
    )
