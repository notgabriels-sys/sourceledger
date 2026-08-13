"""Tests for canonical declared source-use assessments."""

import hashlib
import importlib


def test_source_assessment_module_is_available():
    """The package exposes an assessment layer separate from TOML parsing."""
    try:
        module = importlib.import_module("sourceledger.service")
    except ModuleNotFoundError:
        module = None

    assert module is not None


def test_assessment_marks_needs_review_source_records_incomplete(tmp_path):
    """A declared unresolved state must become a visible, non-successful review status."""
    plan_path = tmp_path / "sources.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Source records assembled for a pre-release internal review."

[[tracks]]
id = "closing-signal"
number = 2
title = "Closing Signal"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[sources]]
id = "review-fragment"
description = "Short processed percussion fragment"
source_kind = "Third-party audio material"
review_state = "needs_review"
review_next_step = "Identify the original source and review its use before release."

[[sources]]
id = "documented-tone"
description = "Synthesized tone layer"
source_kind = "Original synthesis"
review_state = "documented"
review_next_step = "Retain the declared production note for review."

[[uses]]
track_id = "closing-signal"
source_id = "review-fragment"
usage_note = "Heavily processed transition texture."

[[uses]]
track_id = "opening-signal"
source_id = "documented-tone"
""".lstrip(),
        encoding="utf-8",
    )
    service = importlib.import_module("sourceledger.service")
    assess = getattr(service, "assess", None)

    assert callable(assess)
    assessment = assess(plan_path)
    assert assessment.status.startswith("INCOMPLETE DECLARED SOURCE-USE RECORD")
    assert assessment.plan_sha256 == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert [source.identifier for source in assessment.sources] == [
        "documented-tone",
        "review-fragment",
    ]
    review_source = assessment.sources[1]
    assert review_source.review_state == "needs_review"
    assert [
        (item.track_number, item.track_title, item.usage_note)
        for item in review_source.uses
    ] == [
        (2, "Closing Signal", "Heavily processed transition texture."),
    ]


def test_assessment_keeps_documented_records_complete_but_unverified(tmp_path):
    """No pending state yields a complete local ledger, not a clearance claim."""
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
    service = importlib.import_module("sourceledger.service")

    assessment = service.assess(plan_path)

    assert assessment.status.startswith("DECLARED SOURCE-USE RECORD")
    assert assessment.review_required_count == 0
