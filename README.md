# Sourceledger

Sourceledger is an offline command-line tool for recording **declared** audio/source-use information before a music release. It maps source records to tracks, exposes the records that still need review, and produces a compact review bundle.

It is a workflow record, not legal advice, clearance evidence, or audio analysis. The tool does not inspect source audio, identify an original source, determine permissions, or decide whether material may be released.

## What it does

- Loads one local TOML declaration of tracks, source records, and source-to-track uses.
- Validates track/source references, case-normalized duplicate IDs and duplicate source-use rows, and contiguous track numbering.
- Supports a small declared review-state vocabulary: `documented`, `needs_review`, `unresolved`, and `not_applicable`.
- Returns exit code `2` and an explicit incomplete status whenever any record is declared `needs_review` or `unresolved`.
- Builds a readable source ledger, canonical source-use CSV, and a JSON manifest with plan/artifact SHA-256 fingerprints.
- Keeps local plan/output paths out of machine-readable records and generated artifacts.

## What it never does

- Does not inspect, play, hash, decode, copy, alter, upload, or delete audio/source files.
- Does not verify source origin, clearance, consent, licences, contracts, ownership, accuracy, or release readiness.
- Does not contact contributors, rights holders, licensors, publishers, distributors, platforms, or any network service.
- Does not transform `documented` into an external proof or infer a missing source/permission.

Every result starts with one of these statements:

```text
DECLARED SOURCE-USE RECORD - SOURCE ORIGIN, CLEARANCE, CONSENT, LICENSING, ACCURACY, AND RELEASE-READINESS STATUS UNVERIFIED
```

```text
INCOMPLETE DECLARED SOURCE-USE RECORD - ONE OR MORE DECLARED SOURCE RECORDS ARE MARKED NEEDS_REVIEW OR UNRESOLVED; SOURCE ORIGIN, CLEARANCE, CONSENT, LICENSING, ACCURACY, AND RELEASE-READINESS STATUS UNVERIFIED
```

## Install

Requires Python 3.11 or newer.

```bash
python3 -m pip install .
```

For development:

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest
```

## Create a declaration

Start from [examples/sourceledger-example.toml](examples/sourceledger-example.toml). It contains fictional data only.

```toml
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Source records assembled for a pre-release internal review; verify every declaration independently before external use."

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
notes = "Optional local context only."

[[uses]]
track_id = "opening-signal"
source_id = "percussion-fragment"
usage_note = "Optional description of how the declared source is used."
```

All `tracks`, `sources`, and `uses` sections need at least one row. IDs are case-insensitive references. Every source use must refer to a declared track and source, and each track/source relationship is allowed once.

### Review states

| State | Local ledger meaning |
| --- | --- |
| `documented` | Information was entered into this declaration. It is not verified evidence of origin, permission, or readiness. |
| `needs_review` | The declaration says a separate review step remains; the command exits `2`. |
| `unresolved` | The declaration says an issue remains unresolved; the command exits `2`. |
| `not_applicable` | The user declares the review label does not apply to that record; this is not independently verified. |

`source_kind` is your own descriptive field. The tool does not assign legal or technical meaning to it.

## Check without writing files

`check` validates and prints a declared source-use record. It does not write a directory.

```bash
sourceledger check ./sources.toml
sourceledger check ./sources.toml --json
```

The JSON includes the exact plan SHA-256 and declared records, but never the local plan path.

## Build a review bundle

`build` writes only to a **new** output directory. It refuses to replace an existing directory. It may still build an explicitly incomplete record so that the required manual follow-up is documented.

```bash
sourceledger build ./sources.toml \
  --output ./reviews/example-release-sources
```

It creates:

- `SOURCE_LEDGER.md` — readable declared source records, uses, states, next steps, and evidence boundary.
- `source-uses.csv` — one canonical row for each declared source use; sources with no declared use remain visible with blank track fields.
- `manifest.json` — structured declared records, status, source-review count, plan SHA-256, and hashes of the other artifacts.

For path-free machine-readable output:

```bash
sourceledger build ./sources.toml \
  --output ./reviews/example-release-sources \
  --json
```

## Exit codes and interpretation

| Exit code | Meaning |
| ---: | --- |
| `0` | The local declaration is internally consistent and contains no `needs_review` or `unresolved` source record. This is not clearance or release-readiness proof. |
| `2` | The ledger is internally valid but has one or more declared source records that need separate review or remain unresolved. A review bundle can still be built. |
| `1` | The plan or requested output location is invalid; no new bundle is written. |

Before external use, follow each declared next step, compare against the real production context, and verify origin, permissions, licences, consent, agreements, platform requirements, and saved/public fields through separate appropriate processes.

## Test

```bash
python3 -m pytest
```

## License

[MIT](LICENSE)
