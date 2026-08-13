"""Typed loading for declared source-use plans."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REVIEW_STATES = frozenset(
    {"documented", "needs_review", "unresolved", "not_applicable"}
)


class PlanValidationError(ValueError):
    """A declared source-use plan is incomplete or cannot be interpreted safely."""


@dataclass(frozen=True)
class Track:
    identifier: str
    number: int
    title: str


@dataclass(frozen=True)
class SourceRecord:
    identifier: str
    description: str
    source_kind: str
    review_state: str
    review_next_step: str
    notes: str


@dataclass(frozen=True)
class SourceUse:
    track_id: str
    source_id: str
    usage_note: str


@dataclass(frozen=True)
class SourcePlan:
    title: str
    primary_artist: str
    requirements_basis: str
    tracks: tuple[Track, ...]
    sources: tuple[SourceRecord, ...]
    uses: tuple[SourceUse, ...]


def load_plan(path: Path) -> SourcePlan:
    """Load one UTF-8 TOML declaration into typed local source-use records."""
    return load_plan_bytes(path.read_bytes())


def load_plan_bytes(contents: bytes) -> SourcePlan:
    """Load exact plan bytes so a caller can retain a source fingerprint."""
    try:
        data = tomllib.loads(contents.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise PlanValidationError("plan must be UTF-8 encoded TOML") from error
    release = _section(data, "release")
    plan = SourcePlan(
        title=_non_empty_string(release, "title", "release.title"),
        primary_artist=_non_empty_string(
            release, "primary_artist", "release.primary_artist"
        ),
        requirements_basis=_non_empty_string(
            release, "requirements_basis", "release.requirements_basis"
        ),
        tracks=tuple(
            _track(item, index) for index, item in enumerate(_records(data, "tracks"))
        ),
        sources=tuple(
            _source(item, index) for index, item in enumerate(_records(data, "sources"))
        ),
        uses=tuple(
            _use(item, index) for index, item in enumerate(_records(data, "uses"))
        ),
    )
    _validate_unique_track_ids(plan.tracks)
    _validate_track_numbers(plan.tracks)
    _validate_unique_source_ids(plan.sources)
    _validate_references(plan)
    _validate_unique_source_uses(plan.uses)
    return plan


def _track(item: Any, index: int) -> Track:
    name = f"tracks[{index}]"
    return Track(
        identifier=_non_empty_string(item, "id", f"{name}.id"),
        number=_positive_integer(item, "number", f"{name}.number"),
        title=_non_empty_string(item, "title", f"{name}.title"),
    )


def _source(item: Any, index: int) -> SourceRecord:
    name = f"sources[{index}]"
    review_state = _non_empty_string(item, "review_state", f"{name}.review_state")
    if review_state not in REVIEW_STATES:
        states = ", ".join(sorted(REVIEW_STATES))
        raise PlanValidationError(f"{name}.review_state must be one of: {states}")
    return SourceRecord(
        identifier=_non_empty_string(item, "id", f"{name}.id"),
        description=_non_empty_string(item, "description", f"{name}.description"),
        source_kind=_non_empty_string(item, "source_kind", f"{name}.source_kind"),
        review_state=review_state,
        review_next_step=_non_empty_string(
            item, "review_next_step", f"{name}.review_next_step"
        ),
        notes=_optional_string(item, "notes", f"{name}.notes"),
    )


def _use(item: Any, index: int) -> SourceUse:
    name = f"uses[{index}]"
    return SourceUse(
        track_id=_non_empty_string(item, "track_id", f"{name}.track_id"),
        source_id=_non_empty_string(item, "source_id", f"{name}.source_id"),
        usage_note=_optional_string(item, "usage_note", f"{name}.usage_note"),
    )


def _records(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise PlanValidationError(f"{key} must contain at least one TOML table")
    if not all(isinstance(item, dict) for item in value):
        raise PlanValidationError(f"{key} must be a list of TOML tables")
    return value


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PlanValidationError(f"{key} must be a TOML table")
    return value


def _non_empty_string(section: Any, key: str, name: str) -> str:
    if not isinstance(section, dict) or key not in section:
        raise PlanValidationError(f"{name} is required")
    value = section[key]
    if not isinstance(value, str) or not value.strip():
        raise PlanValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_string(section: Any, key: str, name: str) -> str:
    if key not in section:
        return ""
    value = section[key]
    if not isinstance(value, str):
        raise PlanValidationError(f"{name} must be a string")
    return value.strip()


def _positive_integer(section: Any, key: str, name: str) -> int:
    if not isinstance(section, dict) or key not in section:
        raise PlanValidationError(f"{name} is required")
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PlanValidationError(f"{name} must be a positive integer")
    return value


def _validate_references(plan: SourcePlan) -> None:
    track_ids = {track.identifier.casefold() for track in plan.tracks}
    source_ids = {source.identifier.casefold() for source in plan.sources}
    for source_use in plan.uses:
        if source_use.track_id.casefold() not in track_ids:
            raise PlanValidationError("use reference names an undeclared track")
        if source_use.source_id.casefold() not in source_ids:
            raise PlanValidationError("use reference names an undeclared source")


def _validate_unique_source_ids(sources: tuple[SourceRecord, ...]) -> None:
    seen: set[str] = set()
    for source in sources:
        normalized = source.identifier.casefold()
        if normalized in seen:
            raise PlanValidationError("duplicate source id after case normalization")
        seen.add(normalized)


def _validate_track_numbers(tracks: tuple[Track, ...]) -> None:
    actual = sorted(track.number for track in tracks)
    expected = list(range(1, len(tracks) + 1))
    if actual != expected:
        raise PlanValidationError("track numbers must be contiguous from 1")


def _validate_unique_track_ids(tracks: tuple[Track, ...]) -> None:
    seen: set[str] = set()
    for track in tracks:
        normalized = track.identifier.casefold()
        if normalized in seen:
            raise PlanValidationError("duplicate track id after case normalization")
        seen.add(normalized)


def _validate_unique_source_uses(uses: tuple[SourceUse, ...]) -> None:
    seen: set[tuple[str, str]] = set()
    for source_use in uses:
        key = (source_use.track_id.casefold(), source_use.source_id.casefold())
        if key in seen:
            raise PlanValidationError(
                "duplicate source-use entry after case normalization"
            )
        seen.add(key)
