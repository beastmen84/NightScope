"""Protect pinned OpenNGC transformation, identities, metadata, and deterministic seeds."""

from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

from astro_viewer.tools.audit_catalogue_editorial import (
    _ManifestRecord,
    _ngc_remediation_history_errors,
    _repeated_sentence_errors,
    _repeated_sentence_groups,
    _season_reference_errors,
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
    assert report.completed_objects == 323
    assert report.completed_ngc_objects == 95
    assert report.remaining_ngc_objects == 7_271
    assert report.accepted_batches == 13
    assert report.accepted_enrichment_batches == 3
    assert report.accepted_remediation_batches == 10
    assert report.remediated_baseline_objects == 219
    assert report.draft_batches == 0
    assert report.baseline_description_template_families == 0
    assert report.baseline_description_template_objects == 0
    assert report.baseline_observing_template_families == 0
    assert report.baseline_observing_template_objects == 0
    assert report.repeated_sentence_families == 0
    assert report.repeated_sentence_objects == 0
    assert report.warnings == ()


def test_editorial_visual_samples_are_read_from_the_planetary_nebula_manifest() -> None:
    manifest = (
        PROJECT_ROOT
        / "astro_viewer"
        / "data"
        / "editorial_batches"
        / "batch_1_46_9.json"
    )

    assert _sample_ids(manifest) == [
        "ngc-NGC1360",
        "ngc-NGC1514",
        "ngc-NGC2371",
        "ngc-NGC5189",
        "ngc-NGC6572",
        "ngc-NGC7027",
    ]


def test_planetary_enrichment_keeps_physical_aliases_and_catalogue_defaults() -> None:
    manifest = json.loads(
        (PROJECT_ROOT / "astro_viewer/data/editorial_batches/batch_1_46_9.json")
        .read_text(encoding="utf-8")
    )
    entries = {item["object_id"]: item for item in manifest["objects"]}
    expected_numbers = (
        1360, 1501, 1514, 1535, 2346, 2371, 2438, 2440, 2899, 5189,
        6153, 6210, 6369, 6537, 6572, 6741, 6751, 6818, 6891, 7027,
    )
    assert len(manifest["objects"]) == len(entries) == 20
    assert set(entries) == {f"ngc-NGC{number}" for number in expected_numbers}
    assert entries["ngc-NGC2371"]["designations"] == ["NGC 2371", "NGC 2372"]
    assert manifest["batch_kind"] == "ngc_enrichment"
    assert manifest["status"] == "accepted"

    with DEFAULT_OBJECTS.open(encoding="utf-8", newline="") as file:
        catalogue = {row["object_id"]: row for row in csv.DictReader(file)}
    for object_id in entries:
        assert catalogue[object_id]["tipo"] == "Planetary nebula"
        assert catalogue[object_id]["descrizione"] == "Work in progress"
        assert catalogue[object_id]["recommendation_enabled_by_default"] == "0"
    assert "ngc-NGC2372" not in catalogue


@pytest.mark.parametrize(
    ("language", "value", "valid"),
    (
        ("it", "Primavera", False),
        ("en", "Winter; circumpolar from northern latitudes", False),
        ("es", "Otoño, cerca de la culminación", False),
        ("it", "Primavera boreale (autunno australe)", True),
        ("en", "Northern autumn and winter (southern spring and summer)", True),
        ("es", "Finales de invierno y primavera boreales (finales de verano y otoño australes)", True),
        ("it", "Estate australe, culminazione alta", True),
        ("en", "Southern summer, near culmination", True),
        ("es", "Verano austral", True),
        ("it", "Da maggio ad agosto; notti senza Luna", True),
        ("en", "Moonless nights near culmination", True),
        ("es", "De agosto a noviembre", True),
        ("it", "Autunno nell'emisfero sud", True),
        ("es", "Primavera en el hemisferio norte", True),
        ("en", "Northern spring; summer", False),
    ),
)
def test_seasonal_guidance_requires_a_local_hemisphere_reference(
    language: str, value: str, valid: bool,
) -> None:
    errors = _season_reference_errors(language, "target", value)
    assert (not errors) is valid
    if not valid:
        assert errors == [f"target: {language} best_seen season lacks an explicit hemisphere"]


def test_review_correction_batches_are_bounded_disjoint_and_field_scoped() -> None:
    seen: set[str] = set()
    for patch, count in ((15, 75), (16, 57), (17, 87), (18, 56)):
        manifest = PROJECT_ROOT / f"astro_viewer/data/editorial_batches/batch_1_46_{patch}.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        entries = payload["objects"]
        ids = {entry["object_id"] for entry in entries}
        assert len(entries) == len(ids) == count <= 100
        assert not ids & seen
        seen.update(ids)
        assert payload["status"] == "accepted"
        assert payload["batch_kind"] == ("ngc_remediation" if patch == 18 else "baseline_remediation")
        for entry in entries:
            expected = ["best_seen"]
            if entry["object_id"] == "ngc-NGC1266":
                expected.append("curiosity_text")
            assert entry["fields"] == expected
    assert len(seen) == 275


def test_ngc1266_curiosity_keeps_both_interpretations_qualified_in_three_languages() -> None:
    with (PROJECT_ROOT / "astro_viewer/data/object_curiosities_seed.csv").open(
        encoding="utf-8-sig", newline="",
    ) as file:
        row = next(row for row in csv.DictReader(file) if row["object_id"] == "ngc-NGC1266")
    texts = {"it": row["curiosity_text"]}
    for language in ("en", "es"):
        pack = json.loads(
            (PROJECT_ROOT / f"astro_viewer/translations/{language}.json").read_text(encoding="utf-8")
        )
        texts[language] = pack["content"]["objects"]["ngc-NGC1266"]["curiosity_text"]
    for language, qualifiers in {
        "it": ("ipotizzano", "potrebbe"),
        "en": ("propose", "may"),
        "es": ("plantean", "podría"),
    }.items():
        assert all(word in texts[language] for word in qualifiers)
        assert "500" in texts[language]
    assert row["source_url"] == "https://science.nasa.gov/missions/hubble/hubble-sights-galaxy-in-transition/"
    assert row["verified"] == "1"


@pytest.mark.parametrize("language", ("it", "en", "es"))
def test_repository_audit_rejects_unqualified_seasons_without_batch(
    language: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from astro_viewer.tools import audit_catalogue_editorial as audit

    if language == "it":
        original_reader = audit._read_csv

        def read_csv(path, required_fields, errors):
            rows = original_reader(path, required_fields, errors)
            if path.name == "object_descriptions_seed.csv":
                for row in rows:
                    if row["object_id"] == "caldwell-C80":
                        row["best_seen"] = "Primavera"
            return rows

        monkeypatch.setattr(audit, "_read_csv", read_csv)
    else:
        original_reader = audit._pack_objects

        def read_pack(path, pack_language, errors):
            objects = original_reader(path, pack_language, errors)
            if pack_language == language:
                objects["caldwell-C80"]["best_seen"] = {
                    "en": "Spring", "es": "Primavera",
                }[language]
            return objects

        monkeypatch.setattr(audit, "_pack_objects", read_pack)

    report = audit.audit_catalogue_editorial()
    assert f"caldwell-C80: {language} best_seen season lacks an explicit hemisphere" in report.errors


@pytest.mark.parametrize(
    ("enrichment_status", "enrichment_patch", "revision_patch", "same_object", "valid"),
    (
        ("accepted", 2, 18, True, True),
        ("accepted", 9, 18, True, True),
        ("draft", 2, 18, True, False),
        ("accepted", 18, 18, True, False),
        ("accepted", 99, 18, True, False),
        ("accepted", 2, 18, False, False),
    ),
)
def test_ngc_revision_requires_earlier_accepted_enrichment(
    enrichment_status: str, enrichment_patch: int, revision_patch: int,
    same_object: bool, valid: bool,
) -> None:
    def record(kind, patch, status, object_id):
        return _ManifestRecord(
            Path(f"batch_1_46_{patch}.json"), f"1.46.{patch}", kind, status,
            (object_id,), frozenset(), frozenset(),
        )

    revision = record("ngc_remediation", revision_patch, "accepted", "ngc-NGC1266")
    enrichment = record(
        "ngc_enrichment", enrichment_patch, enrichment_status,
        "ngc-NGC1266" if same_object else "ngc-NGC1",
    )
    # File paths sort lexically (18 before 2); chronology must use patch numbers.
    errors = _ngc_remediation_history_errors([revision, enrichment])
    assert (not errors) is valid
    if not valid:
        assert "earlier accepted enrichment" in errors[0]


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    (
        (None, None),
        ("fields", "ngc remediation requires at least one field"),
        ("source", "claims outside remediation fields"),
        ("language", "review es must be accepted"),
        ("visual", "normal must be accepted"),
        ("baseline", "restricted to NGC-only IDs"),
        ("new", "earlier accepted enrichment manifest"),
        ("enrichment", "appears in more than one NGC enrichment manifest"),
    ),
)
def test_ngc_remediation_preserves_field_acceptance_and_coverage(
    tmp_path: Path, mutation: str | None, expected_error: str | None,
) -> None:
    payload = json.loads(
        (PROJECT_ROOT / "astro_viewer/data/editorial_batches/batch_1_46_18.json")
        .read_text(encoding="utf-8")
    )
    payload["source_version"] = "1.46.99"
    entry = next(item for item in payload["objects"] if item["object_id"] == "ngc-NGC1266")
    payload["objects"] = [entry]
    sample = payload["visual_review"]["samples"][0]
    payload["visual_review"]["samples"] = [sample]
    if mutation == "fields":
        entry.pop("fields")
    elif mutation == "source":
        entry["sources"][0]["supports"] = ["short_description"]
    elif mutation == "language":
        entry["reviews"]["es"] = "pending"
    elif mutation == "visual":
        sample["normal"] = "pending"
    elif mutation in {"baseline", "new"}:
        entry["object_id"] = sample["object_id"] = (
            "caldwell-C80" if mutation == "baseline" else "ngc-NGC1"
        )
    elif mutation == "enrichment":
        payload["batch_kind"] = "ngc_enrichment"
        entry.pop("fields")
    manifest = tmp_path / "batch_1_46_99.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    report = audit_catalogue_editorial(batch_path=manifest)
    if expected_error:
        assert any(expected_error in error for error in report.errors)
    else:
        assert report.errors == ()
        assert report.accepted_batches == 14
        assert report.accepted_remediation_batches == 11
        assert report.accepted_enrichment_batches == 3
        assert report.remediated_baseline_objects == 219
        assert report.completed_objects == 323
        assert report.completed_ngc_objects == 95
        assert report.remaining_ngc_objects == 7_271


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


def test_sentence_screen_detects_templates_inside_distinct_paragraphs() -> None:
    repeated = (
        "La struttura è diffusa e va letta attraverso variazioni graduali di luminosità; "
        "cielo scuro e campo ampio contano più di forti ingrandimenti."
    )
    values = {
        "iris": "Una nube a riflessione circonda una stella azzurra. " + repeated,
        "variable": repeated + " Il ventaglio cambia per ombre proiettate dalla polvere.",
    }

    assert _template_groups(values) == ()
    assert _repeated_sentence_groups(values) == (("iris", "variable"),)


def test_sentence_screen_normalizes_measurements_and_aliases() -> None:
    values = {
        "first": (
            "For NGC 123 (C1), compare its 2.5 arcminute extent with its integrated "
            "magnitude of 9.2 before selecting an initial field. A compact core."
        ),
        "second": (
            "For NGC 456 (C2), compare its 7.3 arcminute extent with its integrated "
            "magnitude of 8.1 before selecting an initial field. Broad outer arms."
        ),
    }

    assert _repeated_sentence_groups(values) == (("first", "second"),)


def test_sentence_screen_ignores_short_advice_and_one_object_repetition() -> None:
    long_sentence = "A broad outer shell surrounds a much brighter inner ring of glowing gas."
    values = {
        "first": long_sentence + " " + long_sentence + " Use a dark sky.",
        "second": "Use a dark sky. A compact stellar group.",
    }

    assert _repeated_sentence_groups(values) == ()


def test_sentence_waivers_preserve_language_field_pair_and_batch_scope() -> None:
    sentence = "A broad outer shell surrounds a much brighter inner ring of glowing gas."
    values = {"first": sentence, "second": sentence, "unrelated": "A different target."}
    waiver = frozenset({("en", "short_description", "first", "second")})

    assert _repeated_sentence_errors("en", "short_description", values)
    assert not _repeated_sentence_errors(
        "en", "short_description", values, waivers=waiver
    )
    assert _repeated_sentence_errors("es", "short_description", values, waivers=waiver)
    assert _repeated_sentence_errors("en", "observing_notes", values, waivers=waiver)
    assert not _repeated_sentence_errors(
        "en", "short_description", values, selected_ids={"unrelated"}
    )
    assert _repeated_sentence_errors(
        "en", "short_description", values, selected_ids={"first"}
    )


@pytest.mark.parametrize("language", ("en", "es"))
@pytest.mark.parametrize("field", ("short_description", "observing_notes", "curiosity_text"))
def test_repository_audit_rejects_partial_translation_duplicates_without_batch(
    tmp_path: Path,
    language: str,
    field: str,
) -> None:
    for relative in ("astro_viewer/data", "astro_viewer/translations"):
        (tmp_path / relative).mkdir(parents=True)
    for name in (
        "catalogue_objects_seed.csv", "catalogue_designations_seed.csv",
        "object_descriptions_seed.csv", "object_curiosities_seed.csv",
    ):
        relative = Path("astro_viewer/data") / name
        shutil.copyfile(PROJECT_ROOT / relative, tmp_path / relative)
    shutil.copytree(
        PROJECT_ROOT / "astro_viewer/data/editorial_batches",
        tmp_path / "astro_viewer/data/editorial_batches",
    )
    for pack_language in ("en", "es"):
        relative = Path("astro_viewer/translations") / f"{pack_language}.json"
        shutil.copyfile(PROJECT_ROOT / relative, tmp_path / relative)
    pack_path = tmp_path / f"astro_viewer/translations/{language}.json"
    payload = json.loads(pack_path.read_text(encoding="utf-8"))
    shared = " A broad outer shell surrounds a much brighter inner ring of glowing gas."
    for object_id in ("messier-M1", "messier-M2"):
        payload["content"]["objects"][object_id][field] += shared
    pack_path.write_text(json.dumps(payload), encoding="utf-8")

    report = audit_catalogue_editorial(root=tmp_path)

    assert any(
        f"{language} {field}: repeated narrative sentence messier-M1 / messier-M2"
        in error for error in report.errors
    )
    assert report.repeated_sentence_families >= 1
    assert report.repeated_sentence_objects >= 2


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
    assert report.accepted_batches == 14
    assert report.accepted_enrichment_batches == 3
    assert report.accepted_remediation_batches == 11
    # M1 already has an accepted seasonal correction; revisiting its field
    # adds a batch, never another physical object to the remediation count.
    assert report.remediated_baseline_objects == 219


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
