"""Tests for the declared source-use plan loader."""

import importlib

import pytest


def test_source_plan_loader_module_is_available():
    """The package exposes a dedicated loader for one declared source-use plan."""
    try:
        module = importlib.import_module("sourceledger.config")
    except ModuleNotFoundError:
        module = None

    assert module is not None


def test_loads_a_declared_source_use_plan(tmp_path):
    """One local TOML declaration becomes typed tracks, sources, and uses."""
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
    config = importlib.import_module("sourceledger.config")
    load_plan = getattr(config, "load_plan", None)
    load_plan_bytes = getattr(config, "load_plan_bytes", None)

    assert callable(load_plan)
    assert callable(load_plan_bytes)
    plan = load_plan(plan_path)
    assert plan.title == "Example Release"
    assert [(track.identifier, track.number) for track in plan.tracks] == [
        ("opening-signal", 1)
    ]
    assert [(source.identifier, source.review_state) for source in plan.sources] == [
        ("percussion-fragment", "needs_review")
    ]
    assert [(use.track_id, use.source_id, use.usage_note) for use in plan.uses] == [
        (
            "opening-signal",
            "percussion-fragment",
            "Heavily processed transition texture.",
        )
    ]
    assert load_plan_bytes(plan_path.read_bytes()) == plan


def test_rejects_a_use_that_names_an_undeclared_source(tmp_path):
    """Every source-use row must refer to a source declared in this plan."""
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

[[uses]]
track_id = "opening-signal"
source_id = "unknown-source"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("sourceledger.config")

    with pytest.raises(config.PlanValidationError, match="undeclared source"):
        config.load_plan(plan_path)


def test_rejects_duplicate_source_ids_after_case_normalization(tmp_path):
    """A source-use ledger needs one stable ID per declared source record."""
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

[[sources]]
id = "PERCUSSION-FRAGMENT"
description = "Duplicate record"
source_kind = "Third-party audio material"
review_state = "needs_review"
review_next_step = "Review the duplicate record."

[[uses]]
track_id = "opening-signal"
source_id = "percussion-fragment"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("sourceledger.config")

    with pytest.raises(config.PlanValidationError, match="duplicate source"):
        config.load_plan(plan_path)


def test_rejects_noncontiguous_declared_track_numbers(tmp_path):
    """A source-use report needs a stable contiguous track order."""
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

[[tracks]]
id = "closing-signal"
number = 3
title = "Closing Signal"

[[sources]]
id = "percussion-fragment"
description = "Short processed percussion fragment"
source_kind = "Third-party audio material"
review_state = "needs_review"
review_next_step = "Identify the original source and review its use before release."

[[uses]]
track_id = "opening-signal"
source_id = "percussion-fragment"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("sourceledger.config")

    with pytest.raises(config.PlanValidationError, match="contiguous"):
        config.load_plan(plan_path)


def test_rejects_duplicate_track_ids_after_case_normalization(tmp_path):
    """Every source-use target needs one stable track ID."""
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

[[tracks]]
id = "OPENING-SIGNAL"
number = 2
title = "Closing Signal"

[[sources]]
id = "percussion-fragment"
description = "Short processed percussion fragment"
source_kind = "Third-party audio material"
review_state = "needs_review"
review_next_step = "Identify the original source and review its use before release."

[[uses]]
track_id = "opening-signal"
source_id = "percussion-fragment"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("sourceledger.config")

    with pytest.raises(config.PlanValidationError, match="duplicate track"):
        config.load_plan(plan_path)


def test_rejects_duplicate_source_use_after_case_normalization(tmp_path):
    """One track/source relationship appears once in a canonical source-use ledger."""
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

[[uses]]
track_id = "opening-signal"
source_id = "percussion-fragment"

[[uses]]
track_id = "OPENING-SIGNAL"
source_id = "PERCUSSION-FRAGMENT"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("sourceledger.config")

    with pytest.raises(config.PlanValidationError, match="duplicate source-use"):
        config.load_plan(plan_path)


def test_rejects_an_unknown_declared_review_state(tmp_path):
    """Review-state labels are a small explicit vocabulary, not free-text verdicts."""
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
review_state = "cleared"
review_next_step = "Review the declared source record."

[[uses]]
track_id = "opening-signal"
source_id = "percussion-fragment"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("sourceledger.config")

    with pytest.raises(config.PlanValidationError, match="review_state"):
        config.load_plan(plan_path)
