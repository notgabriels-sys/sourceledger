"""Portable declared source-use review artifacts."""

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .service import SourceAssessment, SourceLedgerAssessment


@dataclass(frozen=True)
class BundleFiles:
    report_path: Path
    uses_path: Path
    manifest_path: Path


def write_bundle(
    *, assessment: SourceLedgerAssessment, output_dir: Path
) -> BundleFiles:
    """Write one new local source-use review bundle from declared data only."""
    _validate_output_dir(output_dir)
    output_dir.mkdir()
    report_path = output_dir / "SOURCE_LEDGER.md"
    uses_path = output_dir / "source-uses.csv"
    manifest_path = output_dir / "manifest.json"
    _write_report(assessment, report_path)
    _write_uses_csv(assessment, uses_path)
    _write_manifest(assessment, manifest_path, (report_path, uses_path))
    return BundleFiles(
        report_path=report_path,
        uses_path=uses_path,
        manifest_path=manifest_path,
    )


def _validate_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        raise ValueError("output_dir must not already exist")
    if not output_dir.parent.is_dir():
        raise ValueError("output_dir parent must be an existing directory")


def _write_report(assessment: SourceLedgerAssessment, path: Path) -> None:
    plan = assessment.plan
    lines = [
        "# Declared source-use ledger",
        "",
        "## Boundary",
        "",
        f"`{assessment.status}`",
        "",
        (
            "This is a local normalization of source records and their declared uses. It does not "
            "inspect audio, determine source origin, verify clearance, consent, licensing, accuracy, "
            "or release readiness, and it does not contact or change any external service."
        ),
        "",
        "## Declared release context",
        "",
        f"- Title: {plan.title}",
        f"- Primary artist: {plan.primary_artist}",
        f"- Requirements basis: {plan.requirements_basis}",
        f"- Source records needing review: {assessment.review_required_count}",
        f"- Plan SHA-256: `{assessment.plan_sha256}`",
        "",
        "## Source records",
        "",
    ]
    for source in assessment.sources:
        lines.extend(_source_markdown(source))
    lines.extend(
        [
            "## Before any separate external action",
            "",
            "- Follow each declared manual next step and compare against the actual production context.",
            "- Confirm origin, permissions, licences, consents, contracts, and any platform/distributor requirements independently.",
            "- Treat a `documented` declaration as a record of supplied information, not proof that it is correct or sufficient.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _source_markdown(source: SourceAssessment) -> list[str]:
    lines = [
        f"### {source.identifier}",
        "",
        f"- Description: {source.description}",
        f"- Declared source kind: {source.source_kind}",
        f"- Declared review state: `{source.review_state}`",
        f"- Manual next step: {source.review_next_step}",
    ]
    if source.notes:
        lines.append(f"- Notes: {source.notes}")
    lines.extend(["", "#### Declared uses", ""])
    if not source.uses:
        lines.extend(["No declared use rows.", ""])
        return lines
    lines.extend(
        [
            "| Track number | Track ID | Track title | Usage note |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for source_use in source.uses:
        lines.append(
            "| "
            f"{source_use.track_number} | {_markdown_cell(source_use.track_id)} | "
            f"{_markdown_cell(source_use.track_title)} | "
            f"{_markdown_cell(source_use.usage_note)} |"
        )
    lines.append("")
    return lines


def _write_uses_csv(assessment: SourceLedgerAssessment, path: Path) -> None:
    fieldnames = [
        "source_id",
        "description",
        "source_kind",
        "review_state",
        "review_next_step",
        "notes",
        "track_number",
        "track_id",
        "track_title",
        "usage_note",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for source in assessment.sources:
            base = {
                "source_id": source.identifier,
                "description": source.description,
                "source_kind": source.source_kind,
                "review_state": source.review_state,
                "review_next_step": source.review_next_step,
                "notes": source.notes,
            }
            if not source.uses:
                writer.writerow(
                    base
                    | {
                        "track_number": "",
                        "track_id": "",
                        "track_title": "",
                        "usage_note": "",
                    }
                )
                continue
            for source_use in source.uses:
                writer.writerow(
                    base
                    | {
                        "track_number": source_use.track_number,
                        "track_id": source_use.track_id,
                        "track_title": source_use.track_title,
                        "usage_note": source_use.usage_note,
                    }
                )


def _write_manifest(
    assessment: SourceLedgerAssessment, path: Path, artifacts: tuple[Path, Path]
) -> None:
    payload = {
        "status": assessment.status,
        "release": {
            "title": assessment.plan.title,
            "primary_artist": assessment.plan.primary_artist,
            "requirements_basis": assessment.plan.requirements_basis,
        },
        "review_required_count": assessment.review_required_count,
        "plan_sha256": assessment.plan_sha256,
        "sources": [_manifest_source(source) for source in assessment.sources],
        "artifacts": [artifact.name for artifact in artifacts],
        "artifact_sha256": {
            artifact.name: hashlib.sha256(artifact.read_bytes()).hexdigest()
            for artifact in artifacts
        },
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _manifest_source(source: SourceAssessment) -> dict[str, object]:
    return {
        "id": source.identifier,
        "description": source.description,
        "source_kind": source.source_kind,
        "review_state": source.review_state,
        "review_next_step": source.review_next_step,
        "notes": source.notes,
        "uses": [
            {
                "track_id": source_use.track_id,
                "track_number": source_use.track_number,
                "track_title": source_use.track_title,
                "usage_note": source_use.usage_note,
            }
            for source_use in source.uses
        ],
    }


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
