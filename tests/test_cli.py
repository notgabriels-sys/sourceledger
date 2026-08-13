"""Tests for the declared source-use command-line interface."""

import hashlib
import importlib
import json


def test_source_cli_module_is_available():
    """The package exposes a command-line entrypoint module."""
    try:
        module = importlib.import_module("sourceledger.cli")
    except ModuleNotFoundError:
        module = None

    assert module is not None


def test_check_reports_an_incomplete_source_review_without_writing(tmp_path, capsys):
    """A review-needed declaration is visible and non-successful without creating files."""
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
""".lstrip(),
        encoding="utf-8",
    )
    cli = importlib.import_module("sourceledger.cli")
    main = getattr(cli, "main", None)

    assert callable(main)
    code = main(["check", str(plan_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["status"].startswith("INCOMPLETE DECLARED SOURCE-USE RECORD")
    assert payload["plan_sha256"] == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert payload["review_required_count"] == 1
    assert payload["sources"][0]["review_state"] == "needs_review"
    assert str(plan_path) not in json.dumps(payload)


def test_build_writes_an_incomplete_bundle_and_returns_two(tmp_path, capsys):
    """Build records declared follow-up work while preserving a non-success exit code."""
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
review_state = "unresolved"
review_next_step = "Identify the original source and review its use before release."

[[uses]]
track_id = "opening-signal"
source_id = "percussion-fragment"
""".lstrip(),
        encoding="utf-8",
    )
    output = tmp_path / "source-review"
    cli = importlib.import_module("sourceledger.cli")

    code = cli.main(["build", str(plan_path), "--output", str(output), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["artifacts"] == [
        "SOURCE_LEDGER.md",
        "source-uses.csv",
        "manifest.json",
    ]
    assert output.joinpath("SOURCE_LEDGER.md").is_file()
    assert output.joinpath("source-uses.csv").is_file()
    assert output.joinpath("manifest.json").is_file()
    assert str(output) not in json.dumps(payload)
