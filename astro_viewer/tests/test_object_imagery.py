"""Protect shared image categories, honest provenance, and legacy-image retirement."""

from __future__ import annotations

import csv
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from PIL import Image

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.object_image_repository import ObjectImageRepository
from astro_viewer.app.services.object_imagery import (
    CATEGORY_IMAGE_KEYS,
    SOLAR_SYSTEM_IMAGE_IDS,
    category_image,
    image_category,
    resolve_object_image,
    retired_builtin_image,
)
from astro_viewer.app.services.localization import activate_language_pack
from astro_viewer.tests.test_phase6_real_data import _controller
from astro_viewer.tools.check_object_images import validate_images


@pytest.mark.parametrize(
    "object_type,category",
    [
        ("Galaxy", "galaxy"), ("Spiral galaxy", "galaxy"),
        ("Elliptical galaxy", "galaxy"), ("Galaxy pair", "galaxy_system"),
        ("Galaxy triplet", "galaxy_system"), ("Galaxy group", "galaxy_system"),
        ("Open cluster", "open_cluster"), ("Globular cluster", "globular_cluster"),
        ("Nebula", "nebula"), ("Diffuse nebula", "nebula"),
        ("Emission nebula", "emission_nebula"),
        ("H II region nebula (part of the Orion Nebula)", "emission_nebula"),
        ("Reflection nebula", "reflection_nebula"), ("Dark nebula", "dark_nebula"),
        ("Planetary nebula", "planetary_nebula"),
        ("Nebula with cluster", "nebula_cluster"),
        ("H II region nebula with cluster", "nebula_cluster"),
        ("Supernova remnant", "supernova_remnant"), ("Asterism", "asterism"),
        ("Milky Way star cloud", "star_cloud"), ("Star", "star"),
        ("Optical Double", "double_star"), ("Unclassified object", "unclassified"),
        ("Future unknown type", "unclassified"), ("", "unclassified"),
        ("  PLANETARY   NEBULA ", "planetary_nebula"),
    ],
)
def test_exact_category_mapping_and_neutral_unknown_fallback(object_type, category):
    assert image_category(object_type) == category


def test_all_seeded_catalogues_share_the_type_policy():
    data_dir = Path(__file__).resolve().parents[1] / "data"
    with (data_dir / "catalogue_objects_seed.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    seen = {}
    for row in rows:
        selected = resolve_object_image(row["object_id"], row["tipo"], {})
        assert selected["kind"] == "illustration"
        assert selected["verified"] is False
        assert selected["source_url"] == ""
        assert selected["image_path"] == seen.setdefault(row["tipo"], selected["image_path"])
        if row["tipo"] != "Unclassified object":
            assert selected["category"] != "unclassified", row["tipo"]
    assert set(image_category(name) for name in seen) == set(CATEGORY_IMAGE_KEYS)


@pytest.mark.parametrize("object_id", sorted(SOLAR_SYSTEM_IMAGE_IDS))
def test_solar_system_default_and_personal_precedence(object_id):
    default = resolve_object_image(object_id, "Planet", {})
    assert default["kind"] == "solar_system"
    assert default["image_path"] == f"resources/images/solar_system/{object_id}.jpg"
    personal = {"image_path": "user/personal.jpg", "license": "User supplied"}
    assert resolve_object_image(object_id, "Planet", {object_id: personal}) == {
        **personal, "kind": "personal", "category": "",
    }


@pytest.mark.parametrize("object_id", ["messier-M31", "caldwell-C23", "ngc-NGC7000"])
def test_personal_deep_sky_image_survives_category_resolution(object_id):
    custom = {"image_path": "user/personal.jpg", "license": "User supplied"}
    result = resolve_object_image(object_id, "Galaxy", {object_id: custom})
    assert result["image_path"] == custom["image_path"]
    assert result["kind"] == "personal"
    assert custom == {"image_path": "user/personal.jpg", "license": "User supplied"}


def test_retirement_requires_matching_identity_path_and_license():
    original = {
        "object_id": "messier-M31",
        "image_path": "resources/images/catalogue/messier-M31.jpg",
        "license": "2MASS public survey data; CDS/P/2MASS/color HiPS ODbL-1.0",
    }
    assert retired_builtin_image(original)
    for changed in (
        {"license": "User supplied"}, {"image_path": "user/personal.jpg"},
        {"object_id": "custom-target"}, {"image_path": "resources/images/catalogue/other.jpg"},
    ):
        assert not retired_builtin_image({**original, **changed})
    assert resolve_object_image("messier-M31", "Galaxy", {"messier-M31": original}) == (
        category_image("galaxy")
    )


def test_retirement_does_not_match_a_catalogue_prefix_alone():
    for object_id in (
        "messier-M0", "messier-M111", "messier-M01", "messier-M31-personal",
        "caldwell-C0", "caldwell-C110", "caldwell-C01", "caldwell-C23-personal",
    ):
        for license_label in (
            "2MASS public survey data; CDS/P/2MASS/color HiPS ODbL-1.0",
            "NightScope local generated asset",
        ):
            row = {
                "object_id": object_id,
                "image_path": f"resources/images/catalogue/{object_id}.jpg",
                "license": license_label,
            }
            assert not retired_builtin_image(row), object_id


def test_upgrade_retires_shipped_photos_but_keeps_custom_metadata(tmp_path):
    database = tmp_path / "nightscope.db"
    schema = Path(__file__).resolve().parents[1] / "data/schema.sql"
    initialize_database(database, schema)
    records = [
        ("messier-M31", "resources/images/catalogue/messier-M31.jpg",
         "2MASS public survey data; CDS/P/2MASS/color HiPS ODbL-1.0"),
        ("caldwell-C33", "resources/images/catalogue/caldwell-C33.jpg",
         "Pan-STARRS1 public data; CDS Pan-STARRS DR1 HiPS ODbL-1.0"),
        ("caldwell-C74", "resources/images/catalogue/caldwell-C74.jpg",
         "SkyMapper DR4 public data; CDS SkyMapper DR4 HiPS ODbL-1.0"),
        ("messier-default-cluster", "resources/images/m13.svg", "NightScope local generated asset"),
        ("messier-M1", "user/m1.jpg", "User supplied"),
        ("caldwell-C23", "user/c23.jpg", "User supplied"),
        ("messier-M111", "resources/images/catalogue/messier-M111.jpg",
         "2MASS public survey data; CDS/P/2MASS/color HiPS ODbL-1.0"),
        ("caldwell-C23-personal", "resources/images/catalogue/caldwell-C23-personal.jpg",
         "NightScope local generated asset"),
    ]
    with closing(sqlite3.connect(database)) as connection:
        connection.executemany(
            "INSERT INTO ObjectImages (object_id, image_path, license, attribution) VALUES (?, ?, ?, 'fixture')",
            records,
        )
        connection.execute("PRAGMA user_version = 25")
        connection.commit()
    initialize_database(database, schema)
    repository = ObjectImageRepository(database)
    for object_id, _, _ in records[:4]:
        assert repository.get(object_id) is None
    for object_id, path, license_label in records[4:]:
        row = repository.get(object_id)
        assert (row["image_path"], row["license"], row["attribution"]) == (path, license_label, "fixture")
    before = repository.all()
    initialize_database(database, schema)
    assert repository.all() == before
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_category_metadata_is_independent_and_never_claims_target_verification():
    first = category_image("galaxy")
    first["verified"] = True
    assert category_image("galaxy")["verified"] is False
    assert category_image("missing") == category_image("unclassified")


@pytest.mark.parametrize("language", ["it", "en", "es"])
def test_controller_uses_canonical_types_across_languages_and_aliases(language):
    data_dir = Path(__file__).resolve().parents[1]
    with _controller() as controller:
        pack = json.loads((data_dir / "translations" / f"{language}.json").read_text(encoding="utf-8"))
        activate_language_pack(pack)
        try:
            for identifier, object_id, category in (
                ("M31", "messier-M31", "galaxy"),
                ("NGC 224", "messier-M31", "galaxy"),
                ("C33", "caldwell-C33", "supernova_remnant"),
                ("NGC 1", "ngc-NGC1", "galaxy"),
            ):
                controller.selectCatalogueObject(identifier)
                selected = controller.selectedObject
                assert selected["id"] == object_id
                assert selected["image"] == category_image(category)["image_path"]
                assert selected["imageKind"] == "illustration"
                assert selected["imageCategory"] == category
                assert not selected["imageVerified"]
                assert not selected["imageSourceUrl"]
        finally:
            activate_language_pack({})


def test_bundled_image_contract_is_complete_and_compact():
    count, total_bytes = validate_images()
    assert count == 25
    # Old deep-sky cutouts alone occupied 15,235,688 bytes. Prevent accidental
    # shipping of the high-resolution generation originals in the new family.
    assert total_bytes < 2_000_000


@pytest.mark.parametrize("damage", [
    "missing", "corrupt", "size", "mode", "blank", "extra", "retired", "seed", "type",
    "manifest_hash", "manifest_inventory", "manifest_total",
])
def test_image_validator_rejects_incomplete_or_inconsistent_bundles(tmp_path, damage):
    source = Path(__file__).resolve().parents[1]
    target = tmp_path / "astro_viewer"
    for folder in ("categories", "solar_system"):
        shutil.copytree(source / "resources/images" / folder, target / "resources/images" / folder)
    (target / "data").mkdir()
    (tmp_path / "docs").mkdir()
    manifest_path = tmp_path / "docs/IMAGE_ASSET_MANIFEST.json"
    shutil.copy2(source.parent / "docs/IMAGE_ASSET_MANIFEST.json", manifest_path)
    for filename in ("object_images_seed.csv", "catalogue_objects_seed.csv"):
        shutil.copy2(source / "data" / filename, target / "data" / filename)
    image_path = target / "resources/images/categories/galaxy.jpg"
    if damage == "missing":
        image_path.unlink()
    elif damage == "corrupt":
        image_path.write_bytes(b"not an image")
    elif damage == "size":
        Image.new("RGB", (32, 32)).save(image_path)
    elif damage == "mode":
        Image.new("L", (512, 512)).save(image_path)
    elif damage == "blank":
        Image.new("RGB", (512, 512)).save(image_path)
    elif damage == "extra":
        (image_path.parent / "unused.jpg").touch()
    elif damage == "retired":
        legacy = target / "resources/images/catalogue"
        legacy.mkdir()
        (legacy / "messier-M31.jpg").touch()
    elif damage == "seed":
        seed = target / "data/object_images_seed.csv"
        seed.write_text(seed.read_text(encoding="utf-8").replace("jupiter,", "messier-M31,"), encoding="utf-8")
    elif damage == "type":
        seed = target / "data/catalogue_objects_seed.csv"
        seed.write_text(seed.read_text(encoding="utf-8").replace("Spiral galaxy", "Unexpected type"), encoding="utf-8")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if damage == "manifest_hash":
            manifest["assets"][0]["asset_sha256"] = "0" * 64
        elif damage == "manifest_inventory":
            manifest["assets"].pop()
        else:
            manifest["total_bytes"] = 0
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises((ValueError, OSError)):
        validate_images(tmp_path)
