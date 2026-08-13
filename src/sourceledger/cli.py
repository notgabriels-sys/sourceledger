"""Command-line interface for declared source-use review records."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .report import BundleFiles, write_bundle
from .service import SourceLedgerAssessment, assess


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sourceledger",
        description="Validate declared music-source uses without external clearance claims.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "build"):
        subparser = subcommands.add_parser(command)
        subparser.add_argument(
            "plan", type=Path, help="Path to a Sourceledger TOML plan"
        )
        subparser.add_argument(
            "--json",
            action="store_true",
            help="Print a path-free machine-readable declared source-use record",
        )
        if command == "build":
            subparser.add_argument(
                "--output",
                type=Path,
                required=True,
                help="New local directory for source-use review artifacts",
            )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Check or build a declared source-use record without source inspection or external action."""
    args = build_parser().parse_args(argv)
    try:
        assessment = assess(args.plan)
        files: BundleFiles | None = None
        if args.command == "build":
            files = write_bundle(assessment=assessment, output_dir=args.output)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    if args.json:
        payload = _as_json(assessment)
        if files is not None:
            payload["artifacts"] = [
                files.report_path.name,
                files.uses_path.name,
                files.manifest_path.name,
            ]
        print(json.dumps(payload, sort_keys=True))
    else:
        if files is not None:
            print(f"Built {files.report_path}")
            print(f"Built {files.uses_path}")
            print(f"Built {files.manifest_path}")
        _print_summary(assessment)
    return 2 if assessment.status.startswith("INCOMPLETE") else 0


def _print_summary(assessment: SourceLedgerAssessment) -> None:
    print(assessment.status)
    print(
        f"Declared release: {assessment.plan.primary_artist} - {assessment.plan.title}"
    )
    print(f"Source records needing review: {assessment.review_required_count}")
    for source in assessment.sources:
        print(
            f"{source.identifier}: state={source.review_state} uses={len(source.uses)}"
        )
    print(
        "No source origin, clearance, consent, licensing, accuracy, or release-readiness "
        "state is verified."
    )


def _as_json(assessment: SourceLedgerAssessment) -> dict[str, object]:
    return {
        "status": assessment.status,
        "plan_sha256": assessment.plan_sha256,
        "release": {
            "title": assessment.plan.title,
            "primary_artist": assessment.plan.primary_artist,
            "requirements_basis": assessment.plan.requirements_basis,
        },
        "review_required_count": assessment.review_required_count,
        "sources": [
            {
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
            for source in assessment.sources
        ],
        "unverified": [
            "source origin, clearance, consent, licensing, and accuracy are not verified",
            "no audio or source evidence was inspected",
            "no person, service, or platform was contacted or changed",
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
