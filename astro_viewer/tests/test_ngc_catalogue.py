"""Protect pinned OpenNGC transformation, identities, metadata, and deterministic seeds."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from astro_viewer.tools.audit_catalogue_editorial import (
    _template_groups,
    audit_catalogue_editorial,
)
from astro_viewer.tools.audit_curiosity_sources import source_urls
from astro_viewer.tools.render_editorial_samples import _sample_ids
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


def test_editorial_baseline_and_ngc_backlog_are_audited() -> None:
    report = audit_catalogue_editorial()

    assert report.errors == ()
    assert report.catalogue_objects == 7_585
    assert report.ngc_only_objects == 7_366
    assert report.baseline_objects == 228
    assert report.completed_objects == 303
    assert report.completed_ngc_objects == 75
    assert report.remaining_ngc_objects == 7_291
    assert report.accepted_batches == 6
    assert report.accepted_enrichment_batches == 2
    assert report.accepted_remediation_batches == 4
    assert report.remediated_baseline_objects == 126
    assert report.draft_batches == 0
    assert report.baseline_description_template_families == 2
    assert report.baseline_description_template_objects == 4
    assert report.baseline_observing_template_families == 5
    assert report.baseline_observing_template_objects == 51
    assert any("prose debt" in warning for warning in report.warnings)


def test_editorial_visual_samples_are_read_from_the_latest_accepted_manifest() -> None:
    manifest = (
        PROJECT_ROOT
        / "astro_viewer"
        / "data"
        / "editorial_batches"
        / "batch_1_46_6.json"
    )

    assert _sample_ids(manifest) == [
        "caldwell-C103",
        "caldwell-C19",
        "caldwell-C55",
        "messier-M97",
        "caldwell-C4",
        "messier-M16",
        "caldwell-C59",
    ]


def test_editorial_template_screen_ignores_ids_aliases_and_measurements() -> None:
    values = {
        "first": (
            "Per M 42 (NGC 1976, Nebulosa di Orione), usa inizialmente un campo "
            "di 1,5 gradi e 60 ingrandimenti per riconoscere tutta la struttura."
        ),
        "second": (
            "Per M 43 (NGC 1982, Nebulosa di Mairan), usa inizialmente un campo "
            "di 2,0 gradi e 80 ingrandimenti per riconoscere tutta la struttura."
        ),
        "distinct": (
            "Il nucleo stellareggiante emerge ad alta potenza, mentre l'alone diffuso "
            "richiede visione distolta e un fondo cielo molto trasparente."
        ),
    }

    assert _template_groups(values) == (("first", "second"),)


def test_accepted_editorial_batch_requires_all_reviews_and_completed_content(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "batch_1_46_1.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_version": "1.46.1",
                "status": "accepted",
                "selection_basis": "Synthetic acceptance failure.",
                "created_on": "2026-09-04",
                "reviewed_on": "2026-09-04",
                "objects": [
                    {
                        "object_id": "ngc-NGC1",
                        "designations": ["NGC 1"],
                        "sources": [
                            {
                                "label": "Source",
                                "url": "https://example.org/ngc-1",
                                "accessed_on": "2026-09-04",
                                "supports": list(
                                    (
                                        "short_description",
                                        "observing_notes",
                                        "best_seen",
                                        "curiosity_text",
                                    )
                                ),
                            }
                        ],
                        "reviews": {
                            "facts": "accepted",
                            "it": "accepted",
                            "en": "accepted",
                            "es": "pending",
                        },
                    }
                ],
                "visual_review": {
                    "samples": [
                        {
                            "object_id": "ngc-NGC1",
                            "reason": "Synthetic sample.",
                            "normal": "accepted",
                            "red_night_vision": "accepted",
                        }
                    ]
                },
                "similarity_waivers": [],
                "deferred": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report = audit_catalogue_editorial(batch_path=manifest)

    assert any("review es must be accepted" in error for error in report.errors)
    assert any("accepted object lacks complete Italian seeds" in error for error in report.errors)
    assert source_urls(manifest) == ["https://example.org/ngc-1"]


def test_baseline_remediation_manifest_is_field_scoped(tmp_path: Path) -> None:
    manifest = tmp_path / "batch_1_46_99.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_version": "1.46.99",
                "batch_kind": "baseline_remediation",
                "status": "accepted",
                "selection_basis": "Synthetic field-scoped baseline correction.",
                "created_on": "2026-09-04",
                "reviewed_on": "2026-09-04",
                "objects": [
                    {
                        "object_id": "messier-M1",
                        "designations": ["M1", "NGC 1952"],
                        "fields": ["best_seen"],
                        "sources": [
                            {
                                "label": "Source",
                                "url": "https://example.org/m1-season",
                                "accessed_on": "2026-09-04",
                                "supports": ["best_seen"],
                            }
                        ],
                        "reviews": {
                            "facts": "accepted",
                            "it": "accepted",
                            "en": "accepted",
                            "es": "accepted",
                        },
                    }
                ],
                "visual_review": {
                    "samples": [
                        {
                            "object_id": "messier-M1",
                            "reason": "Synthetic baseline sample.",
                            "normal": "accepted",
                            "red_night_vision": "accepted",
                        }
                    ]
                },
                "similarity_waivers": [],
                "deferred": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report = audit_catalogue_editorial(batch_path=manifest)

    assert report.errors == ()
    assert report.accepted_batches == 7
    assert report.accepted_enrichment_batches == 2
    assert report.accepted_remediation_batches == 5
    assert report.remediated_baseline_objects == 127


def test_baseline_remediation_rejects_ngc_only_ids_and_undeclared_claims(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "batch_1_46_98.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_version": "1.46.98",
                "batch_kind": "baseline_remediation",
                "status": "draft",
                "selection_basis": "Synthetic remediation boundary failure.",
                "created_on": "2026-09-04",
                "reviewed_on": None,
                "objects": [
                    {
                        "object_id": "ngc-NGC1",
                        "designations": ["NGC 1"],
                        "fields": ["observing_notes"],
                        "sources": [
                            {
                                "label": "Source",
                                "url": "https://example.org/ngc-1",
                                "accessed_on": "2026-09-04",
                                "supports": ["short_description"],
                            }
                        ],
                        "reviews": {
                            "facts": "pending",
                            "it": "pending",
                            "en": "pending",
                            "es": "pending",
                        },
                    }
                ],
                "visual_review": {"samples": []},
                "similarity_waivers": [],
                "deferred": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report = audit_catalogue_editorial(batch_path=manifest)

    assert any(
        "baseline remediation requires an immutable baseline ID" in error
        for error in report.errors
    )
    assert any(
        "claims outside remediation fields short_description" in error
        for error in report.errors
    )
