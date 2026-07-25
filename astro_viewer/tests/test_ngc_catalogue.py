from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from astro_viewer.tools.update_ngc_catalogue import (
    DEFAULT_DESIGNATIONS,
    DEFAULT_OBJECTS,
    DEFAULT_SOURCE,
    OPENNGC_COMMIT,
    OPENNGC_SOURCE_SHA256,
    validate_catalogue,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_openngc_snapshot_and_generated_seeds_are_reproducible() -> None:
    report = validate_catalogue()

    assert report == {
        "source_commit": OPENNGC_COMMIT,
        "canonical_designations": 7_840,
        "usable_designations": 7_839,
        "physical_ngc_targets": 7_571,
        "existing_identity_matches": 205,
        "new_physical_targets": 7_366,
        "total_physical_targets": 7_585,
        "excluded_nonexistent_entries": 1,
    }
    assert DEFAULT_SOURCE.is_file()
    assert len(OPENNGC_SOURCE_SHA256) == 64


def test_ngc_seed_defaults_and_editorial_placeholders_are_explicit() -> None:
    with DEFAULT_OBJECTS.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        objects = list(csv.DictReader(file))
    with DEFAULT_DESIGNATIONS.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        designations = list(csv.DictReader(file))

    ngc_only = [
        row
        for row in objects
        if row["object_id"].startswith("ngc-")
    ]
    ngc_designations = [
        row
        for row in designations
        if row["catalogue"] == "NGC"
    ]

    assert len(objects) == 7_585
    assert len(ngc_only) == 7_366
    assert len(ngc_designations) == 7_839
    assert all(
        row["recommendation_enabled_by_default"] == "0"
        for row in ngc_only
    )
    assert all(
        row["descrizione"] == "Work in progress"
        for row in ngc_only
    )
    assert all(row["is_primary"] in {"0", "1"} for row in ngc_designations)
    assert "NGC 412" not in {
        row["designation"]
        for row in ngc_designations
    }

    designation_counts = Counter(
        row["object_id"]
        for row in ngc_designations
    )
    designation_identity = {
        row["designation"]: row["object_id"]
        for row in ngc_designations
    }
    assert designation_counts["ngc-NGC6"] == 2
    assert designation_counts["ngc-NGC47"] == 2
    assert designation_counts["messier-M76"] == 2
    assert designation_counts["caldwell-C37"] == 2
    assert designation_counts["caldwell-C49"] == 3
    assert designation_counts["caldwell-C106"] == 1
    assert "ngc-NGC6882" not in designation_counts

    assert designation_identity["NGC 47"] == "ngc-NGC47"
    assert designation_identity["NGC 58"] == "ngc-NGC47"
    assert designation_identity["NGC 104"] == "caldwell-C106"
    assert designation_identity["NGC 2239"] == "caldwell-C49"
    assert designation_identity["NGC 2244"] == "caldwell-C50"
    assert designation_identity["NGC 6882"] == "caldwell-C37"
    assert designation_identity["NGC 6885"] == "caldwell-C37"


def test_openngc_attribution_and_complete_license_are_redistributed() -> None:
    notices = (
        PROJECT_ROOT / "THIRD_PARTY_NOTICES.md"
    ).read_text(encoding="utf-8")
    source_notice = (
        DEFAULT_SOURCE.parent / "README.md"
    ).read_text(encoding="utf-8")
    license_text = (
        PROJECT_ROOT / "OPENNGC_LICENSE.txt"
    ).read_text(encoding="utf-8")

    assert "### OpenNGC" in notices
    assert OPENNGC_COMMIT in notices
    assert OPENNGC_COMMIT in source_notice
    assert OPENNGC_SOURCE_SHA256 in source_notice
    assert license_text.startswith(
        "Creative Commons Attribution-ShareAlike 4.0 International"
    )
