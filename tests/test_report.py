"""Tests for portable declared source-use review artifacts."""

import csv
import hashlib
import importlib
import json

import pytest

from sourceledger.service import assess


def test_source_report_module_is_available():
    """The package exposes a report writer separate from assessment logic."""
    try:
        module = importlib.import_module("sourceledger.report")
    except ModuleNotFoundError:
        module = None

    assert module is not None


def test_writes_an_explicitly_incomplete_declared_source_use_bundle(tmp_path):
    """A review-needed source is preserved in a bundle rather than hidden or resolved."""
    plan_path = tmp_path / "sources.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Source records assembled for a pre-release internal review."

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[sources]]
id = "percussion-fragment"
description = "Short processed percussion fragment"
source_kind = "Third-party audio material"
review_state = "needs_review"
review_next_step = "Identify the original source and review its use before release."
notes = "No external source is inspected by this tool."

[[uses]]
track_id = "opening-signal"
source_id = "percussion-fragment"
usage_note = "Heavily processed transition texture."
""".lstrip(),
        encoding="utf-8",
    )
    assessment = assess(plan_path)
    report = importlib.import_module("sourceledger.report")
    write_bundle = getattr(report, "write_bundle", None)

    assert callable(write_bundle)
    output = tmp_path / "source-review"
    files = write_bundle(assessment=assessment, output_dir=output)
    assert files.report_path.name == "SOURCE_LEDGER.md"
    assert files.uses_path.name == "source-uses.csv"
    assert files.manifest_path.name == "manifest.json"

    rendered = files.report_path.read_text(encoding="utf-8")
    assert assessment.status in rendered
    assert "needs_review" in rendered
    assert "Opening Signal" in rendered
    assert str(plan_path) not in rendered

    with files.uses_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [
        {
            "source_id": "percussion-fragment",
            "description": "Short processed percussion fragment",
            "source_kind": "Third-party audio material",
            "review_state": "needs_review",
            "review_next_step": "Identify the original source and review its use before release.",
            "notes": "No external source is inspected by this tool.",
            "track_number": "1",
            "track_id": "opening-signal",
            "track_title": "Opening Signal",
            "usage_note": "Heavily processed transition texture.",
        }
    ]

    manifest = json.loads(files.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == assessment.status
    assert manifest["plan_sha256"] == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert manifest["artifacts"] == ["SOURCE_LEDGER.md", "source-uses.csv"]
    assert str(plan_path) not in json.dumps(manifest)


def test_refuses_to_replace_an_existing_source_review_directory(tmp_path):
    """A build must not overwrite a previous declared source-use record."""
    plan_path = tmp_path / "sources.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Source records assembled for a pre-release internal review."

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[sources]]
id = "documented-tone"
description = "Synthesized tone layer"
source_kind = "Original synthesis"
review_state = "documented"
review_next_step = "Retain the declared production note for review."

[[uses]]
track_id = "opening-signal"
source_id = "documented-tone"
""".lstrip(),
        encoding="utf-8",
    )
    output = tmp_path / "existing-source-review"
    output.mkdir()
    report = importlib.import_module("sourceledger.report")

    with pytest.raises(ValueError, match="must not already exist"):
        report.write_bundle(assessment=assess(plan_path), output_dir=output)

    assert list(output.iterdir()) == []
