"""Protect schema bootstrap, migrations, seeds, repositories, and database recovery."""

from __future__ import annotations

import csv
import sqlite3
import shutil
import tempfile
import time
import unittest
from collections import Counter
from contextlib import closing
from itertools import combinations
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from astro_viewer.app.astronomy.coordinates import parse_dec_degrees, parse_ra_hours
from astro_viewer.app.database.bootstrap import (
    CATALOGUE_OBSERVATION_TYPES,
    SCHEMA_VERSION,
    _seed_reducer_telescope_compatibility,
    _seed_telescope_catalog,
    _validate_catalogue_seed,
    database_initialization_required,
    initialize_database,
)
from astro_viewer.app.database.equipment_catalog_repository import EquipmentCatalogRepository
from astro_viewer.app.database.catalogue_repository import CatalogueRepository
from astro_viewer.app.database.observation_repository import ObservationRepository
from astro_viewer.app.database.object_image_repository import ObjectImageRepository
from astro_viewer.app.services.object_imagery import (
    CATEGORY_IMAGE_KEYS, SOLAR_SYSTEM_IMAGE_IDS, resolve_object_image,
)
from astro_viewer.app.services.location_preferences import LocationPreferenceStore
from astro_viewer.tests.geonames_fixture import write_small_geonames_fixture


MESSIER_OBJECT_COUNT = 110
CALDWELL_OBJECT_COUNT = 109
CURATED_DEEP_SKY_OBJECT_COUNT = (
    MESSIER_OBJECT_COUNT + CALDWELL_OBJECT_COUNT
)
NGC_DESIGNATION_COUNT = 7_839
NGC_PHYSICAL_OBJECT_COUNT = 7_571
NGC_ONLY_OBJECT_COUNT = 7_366
CATALOGUE_OBJECT_COUNT = (
    CURATED_DEEP_SKY_OBJECT_COUNT + NGC_ONLY_OBJECT_COUNT
)


class DatabaseBootstrapTests(unittest.TestCase):
    def test_catalogue_seed_observation_metadata_is_complete(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        with (data_dir / "catalogue_objects_seed.csv").open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            self.assertIn("max_angular_size_deg", reader.fieldnames or [])
            self.assertIn("recommended_observation_type", reader.fieldnames or [])
            self.assertIn("best_filter_class", reader.fieldnames or [])
            self.assertIn("fallback_filter_class", reader.fieldnames or [])
            self.assertIn("optional_color_filter_class", reader.fieldnames or [])
            self.assertIn("imaging_reducer_recommended", reader.fieldnames or [])
            self.assertIn(
                "recommendation_enabled_by_default",
                reader.fieldnames or [],
            )
            rows = list(reader)

        self.assertEqual(len(rows), CATALOGUE_OBJECT_COUNT)
        for row in rows:
            if row["max_angular_size_deg"]:
                self.assertGreater(
                    float(row["max_angular_size_deg"]),
                    0.0,
                    row["object_id"],
                )
            self.assertGreaterEqual(parse_ra_hours(row["ascensione_retta"]), 0.0)
            self.assertLess(parse_ra_hours(row["ascensione_retta"]), 24.0)
            self.assertGreaterEqual(parse_dec_degrees(row["declinazione"]), -90.0)
            self.assertLessEqual(parse_dec_degrees(row["declinazione"]), 90.0)
            self.assertIn(
                row["recommended_observation_type"],
                CATALOGUE_OBSERVATION_TYPES,
                row["object_id"],
            )
            self.assertIn(row["imaging_reducer_recommended"], {"0", "1"})
            expected_default = (
                "0" if row["object_id"].startswith("ngc-") else "1"
            )
            self.assertEqual(
                row["recommendation_enabled_by_default"],
                expected_default,
            )
        observation_types = {
            row["object_id"]: row["recommended_observation_type"]
            for row in rows
        }
        self.assertEqual(observation_types["messier-M27"], "General")
        self.assertEqual(observation_types["messier-M97"], "General")
        self.assertEqual(observation_types["messier-M107"], "General")
        filter_preferences = {
            row["object_id"]: (
                row["best_filter_class"],
                row["fallback_filter_class"],
                row["optional_color_filter_class"],
            )
            for row in rows
        }
        self.assertEqual(filter_preferences["messier-M1"], ("UHC", "", ""))
        self.assertEqual(filter_preferences["messier-M27"], ("OIII", "", ""))
        self.assertEqual(filter_preferences["messier-M3"], ("", "", ""))
        reducer_preferences = {
            row["object_id"]: row["imaging_reducer_recommended"] == "1"
            for row in rows
        }
        self.assertEqual(sum(reducer_preferences.values()), 53)
        self.assertTrue(reducer_preferences["messier-M31"])
        self.assertTrue(reducer_preferences["caldwell-C20"])
        self.assertFalse(reducer_preferences["messier-M3"])

        with (data_dir / "catalogue_designations_seed.csv").open(
            "r", encoding="utf-8", newline=""
        ) as file:
            designations = list(csv.DictReader(file))
        self.assertEqual(
            len(designations),
            CURATED_DEEP_SKY_OBJECT_COUNT + NGC_DESIGNATION_COUNT,
        )
        self.assertEqual(
            sum(row["catalogue"] == "Messier" for row in designations),
            MESSIER_OBJECT_COUNT,
        )
        self.assertEqual(
            sum(row["catalogue"] == "Caldwell" for row in designations),
            CALDWELL_OBJECT_COUNT,
        )
        self.assertEqual(
            sum(row["catalogue"] == "NGC" for row in designations),
            NGC_DESIGNATION_COUNT,
        )
        self.assertEqual(len({row["object_id"] for row in designations}), CATALOGUE_OBJECT_COUNT)

        caldwell_rows = [row for row in rows if row["object_id"].startswith("caldwell-")]
        self.assertEqual(len(caldwell_rows), CALDWELL_OBJECT_COUNT)
        self.assertEqual(
            sum(row["tipo"] in {"Open cluster", "Globular cluster"} for row in caldwell_rows),
            46,
        )
        self.assertEqual(sum("galaxy" in row["tipo"].lower() for row in caldwell_rows), 35)
        self.assertEqual(
            sum(
                "nebula" in row["tipo"].lower() or row["tipo"] == "Supernova remnant"
                for row in caldwell_rows
            ),
            28,
        )

    def test_catalogue_content_seeds_cover_every_deep_sky_target(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        with (data_dir / "catalogue_objects_seed.csv").open(
            "r", encoding="utf-8", newline=""
        ) as file:
            object_rows = list(csv.DictReader(file))
        with (data_dir / "object_descriptions_seed.csv").open(
            "r", encoding="utf-8", newline=""
        ) as file:
            description_rows = list(csv.DictReader(file))
        with (data_dir / "object_images_seed.csv").open(
            "r", encoding="utf-8", newline=""
        ) as file:
            image_rows = list(csv.DictReader(file))

        object_ids = {
            row["object_id"]
            for row in object_rows
            if not row["object_id"].startswith("ngc-")
        }
        ngc_only_rows = [
            row
            for row in object_rows
            if row["object_id"].startswith("ngc-")
        ]
        descriptions = {row["object_id"]: row for row in description_rows}
        images = {row["object_id"]: row for row in image_rows}
        self.assertEqual(
            len(object_ids),
            CURATED_DEEP_SKY_OBJECT_COUNT,
        )
        self.assertEqual(len(ngc_only_rows), NGC_ONLY_OBJECT_COUNT)
        self.assertTrue(
            all(
                row["descrizione"] == "Work in progress"
                for row in ngc_only_rows
            )
        )
        self.assertTrue(object_ids.issubset(descriptions))
        self.assertEqual(set(images), SOLAR_SYSTEM_IMAGE_IDS)
        illustrations = {}
        for row in object_rows:
            image = resolve_object_image(row["object_id"], row["tipo"], images)
            self.assertEqual(image["kind"], "illustration", row["object_id"])
            self.assertFalse(image["source_url"], row["object_id"])
            self.assertFalse(image["verified"], row["object_id"])
            illustrations[image["category"]] = image
        self.assertEqual(set(illustrations), set(CATEGORY_IMAGE_KEYS))
        for category, image in illustrations.items():
            image_path = data_dir.parent / image["image_path"]
            self.assertTrue(image_path.exists(), category)
            self.assertEqual(image_path.suffix.lower(), ".jpg", category)
            with Image.open(image_path) as opened_image:
                self.assertEqual(opened_image.format, "JPEG", category)
                self.assertEqual(opened_image.mode, "RGB", category)
                self.assertEqual(opened_image.size, (512, 512), category)

        caldwell_ids = {f"caldwell-C{index}" for index in range(1, 110)}
        self.assertEqual(len(caldwell_ids & descriptions.keys()), CALDWELL_OBJECT_COUNT)
        self.assertFalse(caldwell_ids & images.keys())
        for object_id in caldwell_ids:
            description = descriptions[object_id]
            self.assertTrue(description["short_description"].strip(), object_id)
            self.assertTrue(description["observing_notes"].strip(), object_id)
            self.assertTrue(description["best_seen"].strip(), object_id)
            self.assertTrue(description["difficulty_small_scope"].strip(), object_id)

    def test_solar_system_image_seed_uses_source_backed_assets(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        with (data_dir / "object_images_seed.csv").open(
            "r", encoding="utf-8", newline=""
        ) as file:
            images = {row["object_id"]: row for row in csv.DictReader(file)}

        object_ids = {
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
        }
        image_paths = {images[object_id]["image_path"] for object_id in object_ids}
        source_urls = {images[object_id]["source_url"] for object_id in object_ids}
        self.assertEqual(len(image_paths), len(object_ids))
        self.assertEqual(len(source_urls), len(object_ids))

        for object_id in object_ids:
            image = images[object_id]
            image_path = data_dir.parent / image["image_path"]
            self.assertTrue(image_path.exists(), object_id)
            self.assertEqual(image_path.suffix.lower(), ".jpg", object_id)
            self.assertTrue(image["source_url"].startswith("https://science.nasa.gov/"))
            self.assertIn("NASA", image["attribution"])
            self.assertIn("NASA", image["license"])
            self.assertEqual(image["verified"], "1")
            with Image.open(image_path) as opened_image:
                self.assertEqual(opened_image.format, "JPEG", object_id)
                self.assertEqual(opened_image.mode, "RGB", object_id)
                self.assertEqual(opened_image.size, (512, 512), object_id)

    def test_image_seed_upgrades_legacy_assets_without_replacing_user_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    """
                    INSERT INTO ObjectImages (object_id, image_path, attribution, license)
                    VALUES ('messier-M31', 'resources/images/m31.svg', 'NightScope',
                            'NightScope local generated placeholder')
                    """
                )
                connection.execute(
                    """
                    INSERT INTO ObjectImages (object_id, image_path, attribution, license)
                    VALUES ('caldwell-C23', 'user/custom-c23.jpg', 'Personal', 'User supplied')
                    """
                )
                connection.execute(
                    """
                    UPDATE ObjectImages
                    SET image_path = 'resources/images/jupiter.svg',
                        license = 'NightScope local generated asset'
                    WHERE object_id = 'jupiter'
                    """
                )
                connection.execute(
                    """
                    UPDATE ObjectImages
                    SET image_path = 'user/custom-saturn.jpg', license = 'User supplied'
                    WHERE object_id = 'saturn'
                    """
                )
                connection.commit()

            initialize_database(database_path, schema_path)
            repository = ObjectImageRepository(database_path)

            self.assertIsNone(repository.get("messier-M31"))
            self.assertEqual(repository.get("caldwell-C23")["image_path"], "user/custom-c23.jpg")
            self.assertEqual(
                repository.get("jupiter")["image_path"],
                "resources/images/solar_system/jupiter.jpg",
            )
            self.assertEqual(repository.get("saturn")["image_path"], "user/custom-saturn.jpg")

    def test_curiosity_seed_is_complete_source_backed_and_editorially_distinct(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        with (data_dir / "object_descriptions_seed.csv").open(
            "r", encoding="utf-8", newline=""
        ) as file:
            description_ids = {row["object_id"] for row in csv.DictReader(file)}
        with (data_dir / "object_curiosities_seed.csv").open(
            "r", encoding="utf-8", newline=""
        ) as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 323)
        self.assertEqual({row["object_id"] for row in rows}, description_ids)
        texts = [row["curiosity_text"].strip() for row in rows]
        self.assertEqual(len(set(texts)), len(texts))
        self.assertGreaterEqual(min(map(len, texts)), 150)
        self.assertTrue(all(row["source_label"].strip() for row in rows))
        self.assertTrue(all(row["source_url"].startswith("https://") for row in rows))
        self.assertTrue(all(row["verified"] == "1" for row in rows))

        prefixes = Counter(" ".join(text.lower().split()[:4]) for text in texts)
        self.assertLessEqual(max(prefixes.values()), 2)
        token_sets = [
            {token.strip(".,:;!?()") for token in text.lower().split() if token.strip(".,:;!?()")}
            for text in texts
        ]
        max_similarity = max(
            len(left & right) / len(left | right)
            for left, right in combinations(token_sets, 2)
        )
        self.assertLess(max_similarity, 0.5)

    def test_description_seed_is_complete_safe_and_object_specific(self) -> None:
        data_path = Path(__file__).resolve().parents[1] / "data" / "object_descriptions_seed.csv"
        with data_path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 323)
        self.assertEqual(len({row["object_id"] for row in rows}), len(rows))
        descriptions = [row["short_description"].strip() for row in rows]
        observing_notes = [row["observing_notes"].strip() for row in rows]
        self.assertEqual(len(set(descriptions)), len(descriptions))
        self.assertEqual(len(set(observing_notes)), len(observing_notes))

        for values in (descriptions, observing_notes):
            token_sets = [
                {
                    token.strip(".,:;!?()")
                    for token in value.lower().split()
                    if token.strip(".,:;!?()")
                }
                for value in values
            ]
            max_similarity = max(
                len(left & right) / len(left | right)
                for left, right in combinations(token_sets, 2)
            )
            self.assertLess(max_similarity, 0.85)

        sun = next(row for row in rows if row["object_id"] == "sun")
        self.assertIn("davanti all'intera apertura", sun["observing_notes"])
        self.assertIn("non usare filtri solari da oculare", sun["observing_notes"])

    def test_object_content_repository_returns_seeded_curiosity_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            curiosities = ObjectImageRepository(database_path).curiosities()

            self.assertEqual(len(curiosities), 323)
            self.assertIn("stella di neutroni", curiosities["messier-M1"]["curiosity_text"])
            self.assertEqual(curiosities["caldwell-C23"]["source_label"], "NASA Hubble")
            self.assertEqual(curiosities["sun"]["source_label"], "NASA Science")
            self.assertTrue(curiosities["moon"]["verified"])

    def test_catalogue_seed_contains_all_messier_and_caldwell_objects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"

            initialize_database(database_path, schema_path)

            repository = CatalogueRepository(database_path)
            objects = repository.list_objects()
            messier = repository.list_objects("Messier")
            caldwell = repository.list_objects("Caldwell")
            ngc = repository.list_objects("NGC")
            self.assertEqual(len(objects), CATALOGUE_OBJECT_COUNT)
            self.assertEqual(len(messier), MESSIER_OBJECT_COUNT)
            self.assertEqual(len(caldwell), CALDWELL_OBJECT_COUNT)
            self.assertEqual(len(ngc), NGC_PHYSICAL_OBJECT_COUNT)
            self.assertEqual(messier[0]["primary_designation"], "M1")
            self.assertEqual(messier[0]["max_angular_size_deg"], 0.117)
            self.assertEqual(messier[-1]["primary_designation"], "M110")
            self.assertEqual(caldwell[0]["primary_designation"], "C1")
            self.assertEqual(caldwell[-1]["primary_designation"], "C109")
            c23 = repository.get_by_designation("caldwell", "c23")
            self.assertIsNotNone(c23)
            assert c23 is not None
            self.assertEqual(c23["object_id"], "caldwell-C23")
            self.assertEqual(c23["name"], "NGC 891")
            ngc_224 = repository.get_by_designation("NGC", "NGC 224")
            self.assertIsNotNone(ngc_224)
            assert ngc_224 is not None
            self.assertEqual(ngc_224["object_id"], "messier-M31")
            ngc_1 = repository.get_by_designation("NGC", "NGC 1")
            self.assertIsNotNone(ngc_1)
            assert ngc_1 is not None
            self.assertFalse(ngc_1["recommendation_enabled_by_default"])
            self.assertFalse(ngc_1["recommendation_enabled"])
            self.assertIsNone(
                repository.get_by_designation("NGC", "NGC 412")
            )

    def test_catalogue_repository_keeps_one_object_for_multiple_designations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    """
                    INSERT INTO CatalogueDesignation (
                        catalogue, designation, object_id, sort_index, is_primary
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("Secondary", "S31", "messier-M31", 31, 0),
                )
                connection.commit()

            repository = CatalogueRepository(database_path)
            self.assertEqual(len(repository.list_objects()), CATALOGUE_OBJECT_COUNT)
            self.assertEqual(len(repository.list_objects("Secondary")), 1)
            self.assertEqual(
                [item["object_id"] for item in repository.search("S31")],
                ["messier-M31"],
            )
            by_designation = repository.get_by_designation("secondary", "s31")
            self.assertIsNotNone(by_designation)
            assert by_designation is not None
            self.assertEqual(by_designation["object_id"], "messier-M31")
            self.assertEqual(
                by_designation["catalogues"],
                ["Messier", "NGC", "Secondary"],
            )
            self.assertEqual(
                [item["designation"] for item in by_designation["designations"]],
                ["M31", "NGC 224", "S31"],
            )

            with closing(sqlite3.connect(database_path)) as connection:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """
                        INSERT INTO CatalogueDesignation (
                            catalogue, designation, object_id, sort_index, is_primary
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        ("Conflicting", "X31", "messier-M31", 31, 1),
                    )

    def test_catalogue_repository_resolves_same_catalogue_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = (
                Path(__file__).resolve().parents[1]
                / "data"
                / "schema.sql"
            )
            initialize_database(database_path, schema_path)
            repository = CatalogueRepository(database_path)

            ngc_6 = repository.get_by_designation("NGC", "NGC 6")
            ngc_20 = repository.get_by_designation("NGC", "NGC 20")

            self.assertIsNotNone(ngc_6)
            self.assertIsNotNone(ngc_20)
            assert ngc_6 is not None and ngc_20 is not None
            self.assertEqual(ngc_6["object_id"], "ngc-NGC6")
            self.assertEqual(ngc_20["object_id"], "ngc-NGC6")
            self.assertEqual(
                [
                    item["designation"]
                    for item in ngc_6["designations"]
                    if item["catalogue"] == "NGC"
                ],
                ["NGC 6", "NGC 20"],
            )

    def test_schema_18_catalogue_migrates_ngc_aliases_and_keeps_preferences(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = (
                Path(__file__).resolve().parents[1]
                / "data"
                / "schema.sql"
            )
            initialize_database(database_path, schema_path)
            CatalogueRepository(database_path).set_recommendation_enabled(
                "messier-M31",
                False,
            )

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    "DELETE FROM CatalogueDesignation WHERE catalogue = 'NGC'"
                )
                connection.execute(
                    "DELETE FROM CatalogueObject WHERE object_id LIKE 'ngc-%'"
                )
                connection.executescript(
                    """
                    CREATE TABLE CatalogueDesignation_v18 (
                        catalogue TEXT NOT NULL,
                        designation TEXT NOT NULL,
                        object_id TEXT NOT NULL,
                        sort_index INTEGER,
                        is_primary INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (catalogue, designation),
                        UNIQUE (object_id, catalogue),
                        FOREIGN KEY (object_id)
                            REFERENCES CatalogueObject(object_id)
                            ON DELETE CASCADE
                    );
                    INSERT INTO CatalogueDesignation_v18 (
                        catalogue, designation, object_id,
                        sort_index, is_primary
                    )
                    SELECT
                        catalogue, designation, object_id,
                        sort_index, is_primary
                    FROM CatalogueDesignation;
                    DROP TABLE CatalogueDesignation;
                    ALTER TABLE CatalogueDesignation_v18
                    RENAME TO CatalogueDesignation;
                    PRAGMA user_version = 18;
                    """
                )
                connection.commit()

            initialize_database(database_path, schema_path)
            repository = CatalogueRepository(database_path)
            ngc_6 = repository.get_by_designation("NGC", "NGC 6")
            ngc_20 = repository.get_by_designation("NGC", "NGC 20")
            m31 = repository.get_by_designation("Messier", "M31")

            self.assertIsNotNone(ngc_6)
            self.assertIsNotNone(ngc_20)
            self.assertIsNotNone(m31)
            assert ngc_6 is not None and ngc_20 is not None
            assert m31 is not None
            self.assertEqual(ngc_6["object_id"], ngc_20["object_id"])
            self.assertFalse(m31["recommendation_enabled"])
            self.assertEqual(
                len(repository.list_objects()),
                CATALOGUE_OBJECT_COUNT,
            )
            with closing(sqlite3.connect(database_path)) as connection:
                self.assertEqual(
                    connection.execute(
                        "PRAGMA user_version"
                    ).fetchone()[0],
                    SCHEMA_VERSION,
                )

    def test_catalogue_recommendation_preference_survives_reseed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)
            repository = CatalogueRepository(database_path)

            initial = repository.get_by_designation("Messier", "M31")
            self.assertIsNotNone(initial)
            assert initial is not None
            self.assertTrue(initial["recommendation_enabled_by_default"])
            self.assertTrue(initial["recommendation_enabled"])

            repository.set_recommendation_enabled("messier-M31", False)
            with self.assertRaisesRegex(ValueError, "stored catalogue object"):
                repository.set_recommendation_enabled("mars", False)
            initialize_database(database_path, schema_path)

            updated = repository.get_by_designation("Messier", "M31")
            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertTrue(updated["recommendation_enabled_by_default"])
            self.assertFalse(updated["recommendation_enabled"])
            self.assertEqual(
                repository.recommendation_preferences(),
                {"messier-m31": False},
            )

    def test_catalogue_recommendation_bulk_write_is_deduplicated_and_atomic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = (
                Path(__file__).resolve().parents[1]
                / "data"
                / "schema.sql"
            )
            initialize_database(database_path, schema_path)
            repository = CatalogueRepository(database_path)

            repository.set_recommendations_enabled(
                (
                    "messier-M31",
                    "MESSIER-m31",
                    "ngc-NGC1",
                ),
                False,
            )

            self.assertEqual(
                repository.recommendation_preferences(),
                {
                    "messier-m31": False,
                    "ngc-ngc1": False,
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                "missing-target",
            ):
                repository.set_recommendations_enabled(
                    (
                        "messier-M31",
                        "missing-target",
                    ),
                    True,
                )

            self.assertEqual(
                repository.recommendation_preferences(),
                {
                    "messier-m31": False,
                    "ngc-ngc1": False,
                },
            )

    def test_catalogue_identity_merge_migrates_obsolete_ngc_preference(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = (
                Path(__file__).resolve().parents[1]
                / "data"
                / "schema.sql"
            )
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    """
                    INSERT INTO CatalogueObject (
                        object_id, nome, tipo, costellazione, magnitudine,
                        ascensione_retta, declinazione, dimensione_apparente,
                        max_angular_size_deg, recommended_observation_type,
                        best_filter_class, fallback_filter_class,
                        optional_color_filter_class,
                        imaging_reducer_recommended,
                        recommendation_enabled_by_default, descrizione
                    )
                    SELECT
                        'ngc-NGC6882', 'NGC 6882', tipo, costellazione,
                        magnitudine, ascensione_retta, declinazione,
                        dimensione_apparente, max_angular_size_deg,
                        recommended_observation_type, best_filter_class,
                        fallback_filter_class, optional_color_filter_class,
                        imaging_reducer_recommended, 0, 'Work in progress'
                    FROM CatalogueObject
                    WHERE object_id = 'caldwell-C37'
                    """
                )
                connection.execute(
                    """
                    UPDATE CatalogueDesignation
                    SET object_id = 'ngc-NGC6882', is_primary = 1
                    WHERE catalogue = 'NGC' AND designation = 'NGC 6882'
                    """
                )
                connection.execute(
                    """
                    INSERT INTO CatalogueRecommendationPreference (
                        object_id, enabled
                    )
                    VALUES ('ngc-NGC6882', 0)
                    """
                )
                connection.commit()

            initialize_database(database_path, schema_path)
            repository = CatalogueRepository(database_path)
            merged = repository.get_by_designation("NGC", "NGC 6882")

            self.assertIsNotNone(merged)
            assert merged is not None
            self.assertEqual(merged["object_id"], "caldwell-C37")
            self.assertFalse(merged["recommendation_enabled"])
            with closing(sqlite3.connect(database_path)) as connection:
                self.assertIsNone(
                    connection.execute(
                        """
                        SELECT object_id
                        FROM CatalogueObject
                        WHERE object_id = 'ngc-NGC6882'
                        """
                    ).fetchone()
                )
                self.assertIsNone(
                    connection.execute(
                        """
                        SELECT object_id
                        FROM CatalogueRecommendationPreference
                        WHERE object_id = 'ngc-NGC6882'
                        """
                    ).fetchone()
                )

    def test_recommendation_query_filters_ngc_before_astronomy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = (
                Path(__file__).resolve().parents[1]
                / "data"
                / "schema.sql"
            )
            initialize_database(database_path, schema_path)
            repository = CatalogueRepository(database_path)

            initial = repository.list_recommendation_objects()
            self.assertEqual(
                len(initial),
                CURATED_DEEP_SKY_OBJECT_COUNT,
            )
            self.assertNotIn(
                "ngc-NGC1",
                {item["object_id"] for item in initial},
            )

            repository.set_recommendation_enabled("ngc-NGC1", True)

            updated = repository.list_recommendation_objects()
            self.assertEqual(
                len(updated),
                CURATED_DEEP_SKY_OBJECT_COUNT + 1,
            )
            self.assertIn(
                "ngc-NGC1",
                {item["object_id"] for item in updated},
            )

    def test_all_enabled_recommendation_query_keeps_indexed_lookup_cost(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = (
                Path(__file__).resolve().parents[1]
                / "data"
                / "schema.sql"
            )
            initialize_database(database_path, schema_path)
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO
                        CatalogueRecommendationPreference (
                            object_id, enabled
                        )
                    SELECT object_id, 1
                    FROM CatalogueObject
                    """
                )
                connection.commit()

            started = time.perf_counter()
            rows = CatalogueRepository(
                database_path
            ).list_recommendation_objects()
            elapsed = time.perf_counter() - started

            self.assertEqual(len(rows), CATALOGUE_OBJECT_COUNT)
            self.assertLess(
                elapsed,
                8.0,
                "The all-enabled eligibility lookup lost its indexed join.",
            )

    def test_catalogue_normalized_identity_constraints_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """
                        INSERT INTO CatalogueObject
                        SELECT
                            'MESSIER-m1', nome, tipo, costellazione, magnitudine,
                            ascensione_retta, declinazione, dimensione_apparente,
                            max_angular_size_deg, recommended_observation_type,
                            best_filter_class, fallback_filter_class,
                            optional_color_filter_class,
                            imaging_reducer_recommended,
                            recommendation_enabled_by_default, descrizione
                        FROM CatalogueObject
                        WHERE object_id = 'messier-M1'
                        """
                    )

            with closing(sqlite3.connect(database_path)) as connection:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """
                        INSERT INTO CatalogueDesignation (
                            catalogue, designation, object_id, sort_index, is_primary
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        ("messier", "m1", "messier-M1", 999, 0),
                    )

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """
                        INSERT INTO CatalogueDesignation (
                            catalogue, designation, object_id, sort_index, is_primary
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        ("Test", "T1", "missing-object", 1, 1),
                    )

    def test_catalogue_seed_validation_rejects_invalid_identity_rows(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        with (data_dir / "catalogue_objects_seed.csv").open(
            "r", encoding="utf-8", newline=""
        ) as file:
            object_row = next(csv.DictReader(file))
        with (data_dir / "catalogue_designations_seed.csv").open(
            "r", encoding="utf-8", newline=""
        ) as file:
            designation_row = next(csv.DictReader(file))

        _validate_catalogue_seed([object_row], [designation_row])
        with self.assertRaisesRegex(ValueError, "references unknown"):
            _validate_catalogue_seed(
                [object_row],
                [{**designation_row, "object_id": "missing-object"}],
            )
        with self.assertRaisesRegex(ValueError, "one primary designation"):
            _validate_catalogue_seed(
                [object_row],
                [{**designation_row, "is_primary": "0"}],
            )

    def test_equipment_catalog_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            data_dir = Path(__file__).resolve().parents[1] / "data"
            schema_path = data_dir / "schema.sql"

            initialize_database(database_path, schema_path)

            repository = EquipmentCatalogRepository(database_path)
            binoculars = repository.binoculars()
            with (data_dir / "binocular_catalog_seed.csv").open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                self.assertEqual(
                    reader.fieldnames,
                    [
                        "seed_key",
                        "brand",
                        "model",
                        "magnification",
                        "objective_diameter_mm",
                        "image_stabilized",
                    ],
                )
                binocular_seed_count = sum(1 for _ in reader)
            self.assertGreaterEqual(len(repository.brands()), 8)
            self.assertGreaterEqual(len(repository.models()), 12)
            self.assertGreaterEqual(len(repository.eyepieces()), 6)
            self.assertGreaterEqual(len(repository.barlows()), 4)
            hyperion_zoom = next(
                item
                for item in repository.eyepieces()
                if item["brand"] == "Baader" and item["model"] == "Hyperion Zoom 8-24 mm"
            )
            self.assertEqual(hyperion_zoom["zoom_click_positions_mm"], "24;20;16;12;8")
            self.assertEqual(len(binoculars), binocular_seed_count)
            self.assertGreaterEqual(len(binoculars), 60)
            self.assertTrue(any(item["image_stabilized"] for item in binoculars))
            binocular_classes = {
                (item["magnification"], item["objective_diameter_mm"])
                for item in binoculars
            }
            for binocular_class in {
                (7, 50),
                (8, 42),
                (8, 56),
                (10, 42),
                (10, 50),
                (12, 50),
                (15, 56),
                (15, 70),
                (16, 70),
                (20, 80),
                (25, 100),
            }:
                self.assertIn(binocular_class, binocular_classes)
            self.assertIsNotNone(repository.active_profile())

    def test_equipment_seed_keys_are_explicit_unique_and_compatible(self) -> None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        catalog_kinds = {
            "telescope_catalog_seed.csv": "telescope",
            "eyepiece_catalog_seed.csv": "eyepiece",
            "barlow_catalog_seed.csv": "barlow",
            "binocular_catalog_seed.csv": "binocular",
            "astronomy_camera_catalog_seed.csv": "astro-camera",
            "camera_body_catalog_seed.csv": "camera-body",
            "filter_catalog_seed.csv": "filter",
            "reducer_catalog_seed.csv": "reducer",
        }
        keys_by_kind: dict[str, set[str]] = {}

        for filename, kind in catalog_kinds.items():
            with (data_dir / filename).open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                self.assertEqual((reader.fieldnames or [None])[0], "seed_key")
                rows = list(reader)
            seed_keys = [row["seed_key"] for row in rows]
            self.assertTrue(all(key.startswith(f"{kind}::") for key in seed_keys))
            self.assertEqual(len(seed_keys), len(set(seed_keys)))
            keys_by_kind[kind] = set(seed_keys)

        smart_capability_path = (
            data_dir / "smart_telescope_capabilities_seed.csv"
        )
        with smart_capability_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            smart_capability_rows = list(csv.DictReader(file))
        smart_capability_keys = [
            row["seed_key"] for row in smart_capability_rows
        ]
        self.assertEqual(
            len(smart_capability_keys),
            len(set(smart_capability_keys)),
        )
        self.assertTrue(
            set(smart_capability_keys).issubset(
                keys_by_kind["telescope"]
            )
        )

        compatibility_path = data_dir / "reducer_telescope_compatibility_seed.csv"
        with compatibility_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            self.assertEqual(
                (reader.fieldnames or [])[:2],
                ["reducer_seed_key", "telescope_seed_key"],
            )
            compatibility_rows = list(reader)
        self.assertEqual(
            len(compatibility_rows),
            len(
                {
                    (row["reducer_seed_key"], row["telescope_seed_key"])
                    for row in compatibility_rows
                }
            ),
        )
        for row in compatibility_rows:
            self.assertIn(row["reducer_seed_key"], keys_by_kind["reducer"])
            self.assertIn(row["telescope_seed_key"], keys_by_kind["telescope"])

    def test_schema_16_equipment_seed_identity_correction_updates_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            database_path = runtime_dir / "nightscope.db"
            data_dir = Path(__file__).resolve().parents[1] / "data"
            schema_path = data_dir / "schema.sql"
            telescope_path = data_dir / "telescope_catalog_seed.csv"
            compatibility_path = data_dir / "reducer_telescope_compatibility_seed.csv"
            corrected_path = runtime_dir / "telescope_catalog_seed.csv"
            initialize_database(database_path, schema_path)

            target_seed_key = "telescope::celestron::nexstar 5se"
            with compatibility_path.open("r", encoding="utf-8", newline="") as file:
                compatibility_rows = list(csv.DictReader(file))
            self.assertTrue(
                any(
                    row["telescope_seed_key"] == target_seed_key
                    for row in compatibility_rows
                )
            )
            with telescope_path.open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                fieldnames = list(reader.fieldnames or [])
                telescope_rows = list(reader)
            target_row = next(
                row for row in telescope_rows if row["seed_key"] == target_seed_key
            )
            corrected_name = f"{target_row['model']} corrected"
            target_row["model"] = corrected_name
            with corrected_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()
                writer.writerows(telescope_rows)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.row_factory = sqlite3.Row
                original = connection.execute(
                    "SELECT id, name FROM TelescopeModel WHERE seed_key = ?",
                    (target_seed_key,),
                ).fetchone()
                original_count = connection.execute(
                    "SELECT COUNT(*) FROM TelescopeModel"
                ).fetchone()[0]
                original_compatibility_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM ReducerTelescopeCompatibility
                    WHERE telescope_model_id = ?
                    """,
                    (original["id"],),
                ).fetchone()[0]
                self.assertGreater(original_compatibility_count, 0)

                _seed_telescope_catalog(connection, corrected_path)
                _seed_reducer_telescope_compatibility(connection, compatibility_path)

                corrected = connection.execute(
                    "SELECT id, name FROM TelescopeModel WHERE seed_key = ?",
                    (target_seed_key,),
                ).fetchone()
                corrected_count = connection.execute(
                    "SELECT COUNT(*) FROM TelescopeModel"
                ).fetchone()[0]
                corrected_compatibility_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM ReducerTelescopeCompatibility
                    WHERE telescope_model_id = ?
                    """,
                    (corrected["id"],),
                ).fetchone()[0]
                self.assertEqual(corrected["id"], original["id"])
                self.assertEqual(corrected["name"], corrected_name)
                self.assertEqual(corrected_count, original_count)
                self.assertEqual(
                    corrected_compatibility_count,
                    original_compatibility_count,
                )

                connection.execute(
                    """
                    UPDATE TelescopeModel
                    SET name = ?, is_user_modified = 1
                    WHERE id = ?
                    """,
                    ("User telescope name", corrected["id"]),
                )
                target_row["model"] = f"{corrected_name} again"
                with corrected_path.open("w", encoding="utf-8", newline="") as file:
                    writer = csv.DictWriter(
                        file,
                        fieldnames=fieldnames,
                        lineterminator="\n",
                    )
                    writer.writeheader()
                    writer.writerows(telescope_rows)
                _seed_telescope_catalog(connection, corrected_path)

                preserved = connection.execute(
                    """
                    SELECT name, is_user_modified
                    FROM TelescopeModel
                    WHERE seed_key = ?
                    """,
                    (target_seed_key,),
                ).fetchone()
                self.assertEqual(preserved["name"], "User telescope name")
                self.assertEqual(preserved["is_user_modified"], 1)

    def test_legacy_equipment_seed_keys_are_restored_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            table_names = (
                "TelescopeModel",
                "EyepieceCatalog",
                "BarlowCatalog",
                "BinocularCatalog",
                "FilterCatalog",
                "ReducerCatalog",
            )
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                original_counts = {
                    table_name: connection.execute(
                        f"SELECT COUNT(*) FROM {table_name}"
                    ).fetchone()[0]
                    for table_name in table_names
                }
                for table_name in table_names:
                    connection.execute(
                        f"UPDATE {table_name} SET seed_key = NULL WHERE is_builtin = 1"
                    )
                connection.execute("PRAGMA user_version = 15")
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                for table_name in table_names:
                    self.assertEqual(
                        connection.execute(
                            f"SELECT COUNT(*) FROM {table_name}"
                        ).fetchone()[0],
                        original_counts[table_name],
                    )
                    self.assertEqual(
                        connection.execute(
                            f"""
                            SELECT COUNT(*)
                            FROM {table_name}
                            WHERE is_builtin = 1 AND seed_key IS NULL
                            """
                        ).fetchone()[0],
                        0,
                    )

    def test_equipment_seed_identity_collision_preserves_custom_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            database_path = runtime_dir / "nightscope.db"
            data_dir = Path(__file__).resolve().parents[1] / "data"
            telescope_path = data_dir / "telescope_catalog_seed.csv"
            corrected_path = runtime_dir / "telescope_catalog_seed.csv"
            initialize_database(database_path, data_dir / "schema.sql")

            with telescope_path.open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                fieldnames = list(reader.fieldnames or [])
                telescope_rows = list(reader)
            target_row = telescope_rows[0]
            original_name = target_row["model"]
            collision_name = "Custom collision telescope"
            target_row["model"] = collision_name
            with corrected_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()
                writer.writerows(telescope_rows)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.row_factory = sqlite3.Row
                seeded = connection.execute(
                    """
                    SELECT id, brand_id, optical_type, aperture_mm,
                           focal_length_mm, mount_type
                    FROM TelescopeModel
                    WHERE seed_key = ?
                    """,
                    (target_row["seed_key"],),
                ).fetchone()
                connection.execute(
                    """
                    INSERT INTO TelescopeModel (
                        brand_id, name, optical_type, aperture_mm,
                        focal_length_mm, mount_type, is_builtin
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        seeded["brand_id"],
                        collision_name,
                        seeded["optical_type"],
                        seeded["aperture_mm"],
                        seeded["focal_length_mm"],
                        seeded["mount_type"],
                    ),
                )

                with self.assertLogs(
                    "astro_viewer.app.database.bootstrap",
                    level="WARNING",
                ):
                    _seed_telescope_catalog(connection, corrected_path)

                preserved_seed = connection.execute(
                    "SELECT name FROM TelescopeModel WHERE id = ?",
                    (seeded["id"],),
                ).fetchone()
                custom = connection.execute(
                    """
                    SELECT is_builtin, seed_key
                    FROM TelescopeModel
                    WHERE brand_id = ? AND name = ?
                    """,
                    (seeded["brand_id"], collision_name),
                ).fetchone()
                self.assertEqual(preserved_seed["name"], original_name)
                self.assertEqual(custom["is_builtin"], 0)
                self.assertIsNone(custom["seed_key"])

    def test_missing_database_is_bootstrapped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "missing.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"

            initialize_database(database_path, schema_path)

            self.assertTrue(database_path.exists())
            self.assertEqual(
                len(CatalogueRepository(database_path).list_objects()),
                CATALOGUE_OBJECT_COUNT,
            )

    def test_initialization_preflight_detects_first_launch_and_ready_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"

            self.assertTrue(database_initialization_required(database_path, schema_path))

            initialize_database(database_path, schema_path)

            self.assertFalse(database_initialization_required(database_path, schema_path))

    def test_initialization_preflight_detects_empty_seeded_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("DELETE FROM CatalogueObject")
                connection.commit()

            self.assertTrue(database_initialization_required(database_path, schema_path))

    def test_database_initialization_reports_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            messages = []

            initialize_database(database_path, schema_path, progress_callback=messages.append)

            self.assertIn("Creazione database...", messages)
            self.assertIn("Importazione cataloghi...", messages)
            self.assertIn("Finalizzazione...", messages)

    def test_geonames_initialization_reports_incremental_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            write_small_geonames_fixture(runtime_dir, extra_rows=2)
            database_path = runtime_dir / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            messages = []

            initialize_database(
                database_path,
                schema_path,
                progress_callback=messages.append,
                geonames_data_dir=runtime_dir,
            )

            self.assertTrue(any(message.startswith("Importazione catalogo città...") for message in messages))

    def test_database_uses_sqlite_user_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(version, SCHEMA_VERSION)

    def test_seed_data_preserves_marked_user_customizations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    """
                    UPDATE TelescopeModel
                    SET notes = ?, is_user_modified = 1
                    WHERE id = (SELECT MIN(id) FROM TelescopeModel)
                    """,
                    ("modifica utente",),
                )
                telescope_count = connection.execute("SELECT COUNT(*) FROM TelescopeModel").fetchone()[0]
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                preserved_note = connection.execute(
                    "SELECT notes FROM TelescopeModel WHERE id = (SELECT MIN(id) FROM TelescopeModel)"
                ).fetchone()[0]
                preserved_count = connection.execute("SELECT COUNT(*) FROM TelescopeModel").fetchone()[0]
            self.assertEqual(preserved_note, "modifica utente")
            self.assertEqual(preserved_count, telescope_count)

    def test_catalogue_content_seed_refreshes_builtin_and_preserves_custom_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    """
                    UPDATE ObjectDescription
                    SET short_description = ?, is_builtin = 0
                    WHERE object_id = ?
                    """,
                    ("contenuto locale", "messier-M1"),
                )
                connection.execute(
                    """
                    UPDATE ObjectDescription
                    SET short_description = ?
                    WHERE object_id = ?
                    """,
                    ("contenuto seed obsoleto", "messier-M2"),
                )
                connection.execute(
                    """
                    UPDATE ObjectCuriosity
                    SET curiosity_text = ?
                    WHERE object_id = ?
                    """,
                    ("curiosità seed obsoleta", "messier-M2"),
                )
                connection.execute(
                    """
                    UPDATE ObjectCuriosity
                    SET curiosity_text = ?, is_builtin = 0
                    WHERE object_id = ?
                    """,
                    ("curiosità locale", "messier-M1"),
                )
                connection.execute(
                    "DELETE FROM ObjectDescription WHERE object_id = ?",
                    ("caldwell-C109",),
                )
                connection.execute(
                    "DELETE FROM ObjectImages WHERE object_id = ?",
                    ("moon",),
                )
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                preserved = connection.execute(
                    """
                    SELECT short_description, is_builtin
                    FROM ObjectDescription WHERE object_id = ?
                    """,
                    ("messier-M1",),
                ).fetchone()
                refreshed_description = connection.execute(
                    "SELECT short_description FROM ObjectDescription WHERE object_id = ?",
                    ("messier-M2",),
                ).fetchone()[0]
                refreshed_curiosity = connection.execute(
                    "SELECT curiosity_text FROM ObjectCuriosity WHERE object_id = ?",
                    ("messier-M2",),
                ).fetchone()[0]
                preserved_curiosity = connection.execute(
                    """
                    SELECT curiosity_text, is_builtin
                    FROM ObjectCuriosity WHERE object_id = ?
                    """,
                    ("messier-M1",),
                ).fetchone()
                restored_description = connection.execute(
                    "SELECT short_description FROM ObjectDescription WHERE object_id = ?",
                    ("caldwell-C109",),
                ).fetchone()
                restored_image = connection.execute(
                    "SELECT image_path FROM ObjectImages WHERE object_id = ?",
                    ("moon",),
                ).fetchone()
            self.assertEqual(preserved, ("contenuto locale", 0))
            self.assertNotEqual(refreshed_description, "contenuto seed obsoleto")
            self.assertNotEqual(refreshed_curiosity, "curiosità seed obsoleta")
            self.assertEqual(preserved_curiosity, ("curiosità locale", 0))
            self.assertIsNotNone(restored_description)
            self.assertIsNotNone(restored_image)
            self.assertEqual(restored_image[0], "resources/images/solar_system/moon.jpg")

    def test_schema_10_content_rows_are_adopted_as_builtin_and_refreshed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.executescript(
                    """
                    ALTER TABLE ObjectDescription RENAME TO ObjectDescriptionCurrent;
                    CREATE TABLE ObjectDescription (
                        object_id TEXT PRIMARY KEY,
                        short_description TEXT NOT NULL,
                        observing_notes TEXT NOT NULL,
                        best_seen TEXT,
                        difficulty_naked_eye TEXT,
                        difficulty_binocular TEXT,
                        difficulty_small_scope TEXT,
                        difficulty_medium_scope TEXT,
                        difficulty_large_scope TEXT
                    );
                    INSERT INTO ObjectDescription
                    SELECT object_id, short_description, observing_notes, best_seen,
                           difficulty_naked_eye, difficulty_binocular,
                           difficulty_small_scope, difficulty_medium_scope,
                           difficulty_large_scope
                    FROM ObjectDescriptionCurrent;
                    DROP TABLE ObjectDescriptionCurrent;

                    ALTER TABLE ObjectCuriosity RENAME TO ObjectCuriosityCurrent;
                    CREATE TABLE ObjectCuriosity (
                        object_id TEXT PRIMARY KEY,
                        curiosity_text TEXT NOT NULL,
                        source_label TEXT NOT NULL,
                        source_url TEXT NOT NULL,
                        verified INTEGER NOT NULL DEFAULT 0
                    );
                    INSERT INTO ObjectCuriosity
                    SELECT object_id, curiosity_text, source_label, source_url, verified
                    FROM ObjectCuriosityCurrent;
                    DROP TABLE ObjectCuriosityCurrent;
                    """
                )
                connection.execute(
                    "UPDATE ObjectDescription SET short_description = ? WHERE object_id = ?",
                    ("contenuto versione 10", "messier-M1"),
                )
                connection.execute(
                    "UPDATE ObjectCuriosity SET curiosity_text = ? WHERE object_id = ?",
                    ("curiosità versione 10", "messier-M1"),
                )
                connection.execute("PRAGMA user_version = 10")
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                description = connection.execute(
                    """
                    SELECT short_description, is_builtin
                    FROM ObjectDescription WHERE object_id = ?
                    """,
                    ("messier-M1",),
                ).fetchone()
                curiosity = connection.execute(
                    """
                    SELECT curiosity_text, is_builtin
                    FROM ObjectCuriosity WHERE object_id = ?
                    """,
                    ("messier-M1",),
                ).fetchone()
                schema_version = connection.execute("PRAGMA user_version").fetchone()[0]

            self.assertNotEqual(description[0], "contenuto versione 10")
            self.assertEqual(description[1], 1)
            self.assertNotEqual(curiosity[0], "curiosità versione 10")
            self.assertEqual(curiosity[1], 1)
            self.assertEqual(schema_version, SCHEMA_VERSION)

    def test_binocular_catalog_persists_across_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            repository = EquipmentCatalogRepository(database_path)
            initial_count = len(repository.binoculars())
            ok, message = repository.add_binocular(
                "NightScope",
                "Test 10x50",
                10,
                50,
                image_stabilized=True,
            )

            self.assertTrue(ok, message)

            initialize_database(database_path, schema_path)
            binoculars = EquipmentCatalogRepository(database_path).binoculars()
            saved = next(
                item
                for item in binoculars
                if item["brand"] == "NightScope" and item["model"] == "Test 10x50"
            )

            self.assertEqual(len(binoculars), initial_count + 1)
            self.assertEqual(saved["display_name"], "NightScope Test 10x50")
            self.assertEqual(saved["spec_label"], "10×50")
            self.assertTrue(saved["image_stabilized"])

    def test_profile_binocular_assignments_persist_and_do_not_delete_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            repository = EquipmentCatalogRepository(database_path)
            profile = repository.active_profile()
            binocular = next(item for item in repository.binoculars() if item["image_stabilized"])

            repository.assign_profile_binocular(int(profile["id"]), binocular["catalog_id"])

            reopened = EquipmentCatalogRepository(database_path)
            self.assertIn(binocular["catalog_id"], reopened.profile_binocular_ids(int(profile["id"])))
            self.assertEqual(reopened.profile_usage_count("binocular", binocular["catalog_id"]), 1)

            reopened.remove_profile_binocular(int(profile["id"]), binocular["catalog_id"])
            self.assertNotIn(
                binocular["catalog_id"],
                EquipmentCatalogRepository(database_path).profile_binocular_ids(int(profile["id"])),
            )
            self.assertTrue(
                any(item["catalog_id"] == binocular["catalog_id"] for item in EquipmentCatalogRepository(database_path).binoculars())
            )

    def test_binocular_catalog_is_added_to_existing_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("DROP TABLE BinocularCatalog")
                connection.execute("PRAGMA user_version = 1")
                connection.commit()

            self.assertTrue(database_initialization_required(database_path, schema_path))

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                table = connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name = 'BinocularCatalog'
                    """
                ).fetchone()
                columns = [
                    row[1]
                    for row in connection.execute("PRAGMA table_info(BinocularCatalog)").fetchall()
                ]
                version = connection.execute("PRAGMA user_version").fetchone()[0]
            self.assertIsNotNone(table)
            self.assertEqual(
                columns,
                [
                    "id",
                    "brand",
                    "model",
                    "magnification",
                    "objective_diameter_mm",
                    "image_stabilized",
                    "is_builtin",
                    "seed_key",
                    "is_user_modified",
                ],
            )
            self.assertEqual(version, SCHEMA_VERSION)

    def test_binocular_catalog_migration_removes_obsolete_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("ALTER TABLE BinocularCatalog RENAME TO BinocularCatalog_old")
                connection.execute(
                    """
                    CREATE TABLE BinocularCatalog (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        brand TEXT NOT NULL,
                        model TEXT NOT NULL,
                        magnification INTEGER NOT NULL,
                        objective_diameter_mm INTEGER NOT NULL,
                        legacy_real REAL,
                        legacy_integer INTEGER,
                        image_stabilized INTEGER NOT NULL DEFAULT 0,
                        legacy_text TEXT,
                        UNIQUE (brand, model, magnification, objective_diameter_mm)
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO BinocularCatalog (
                        id, brand, model, magnification, objective_diameter_mm,
                        legacy_real, legacy_integer, image_stabilized, legacy_text
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (999, "NightScope", "Legacy 10x50", 10, 50, 6.5, 920, 1, "Legacy"),
                )
                connection.execute("DROP TABLE BinocularCatalog_old")
                connection.execute("PRAGMA user_version = 2")
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                columns = [
                    row[1]
                    for row in connection.execute("PRAGMA table_info(BinocularCatalog)").fetchall()
                ]
                row = connection.execute(
                    """
                    SELECT brand, model, magnification, objective_diameter_mm,
                           image_stabilized, is_builtin
                    FROM BinocularCatalog
                    WHERE id = ?
                    """,
                    (999,),
                ).fetchone()
            self.assertEqual(
                columns,
                [
                    "id",
                    "brand",
                    "model",
                    "magnification",
                    "objective_diameter_mm",
                    "image_stabilized",
                    "is_builtin",
                    "seed_key",
                    "is_user_modified",
                ],
            )
            self.assertEqual(row, ("NightScope", "Legacy 10x50", 10, 50, 1, 0))

    def test_schema_16_renames_seeded_naked_eye_profile_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    "UPDATE EquipmentProfile SET profile_name = ? WHERE id = 1",
                    ("Occhio nudo",),
                )
                connection.execute("PRAGMA user_version = 15")
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                profile_name = connection.execute(
                    "SELECT profile_name FROM EquipmentProfile WHERE id = 1"
                ).fetchone()[0]
            self.assertEqual(profile_name, "Default")

    def test_schema_16_uses_free_default_name_when_user_profile_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    "UPDATE EquipmentProfile SET profile_name = ? WHERE id = 1",
                    ("Occhio nudo",),
                )
                connection.execute(
                    """
                    INSERT INTO EquipmentProfile (profile_name, active, telescope_id)
                    VALUES ('Default', 0, '')
                    """
                )
                connection.execute("PRAGMA user_version = 15")
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                profile_names = connection.execute(
                    "SELECT profile_name FROM EquipmentProfile ORDER BY id"
                ).fetchall()
            self.assertEqual(profile_names, [("Default 2",), ("Default",)])

    def test_profile_binocular_table_is_added_to_existing_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("DROP TABLE EquipmentProfileBinocular")
                connection.execute("PRAGMA user_version = 3")
                connection.commit()

            self.assertTrue(database_initialization_required(database_path, schema_path))

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                table = connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name = 'EquipmentProfileBinocular'
                    """
                ).fetchone()
                version = connection.execute("PRAGMA user_version").fetchone()[0]
            self.assertIsNotNone(table)
            self.assertEqual(version, SCHEMA_VERSION)

    def test_catalogue_seed_restores_missing_rows_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    "UPDATE CatalogueObject SET descrizione = ? WHERE object_id = ?",
                    ("nota locale", "messier-M1"),
                )
                connection.execute(
                    "DELETE FROM CatalogueObject WHERE object_id = ?",
                    ("messier-M110",),
                )
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                row_count = connection.execute("SELECT COUNT(*) FROM CatalogueObject").fetchone()[0]
                preserved_description = connection.execute(
                    "SELECT descrizione FROM CatalogueObject WHERE object_id = ?",
                    ("messier-M1",),
                ).fetchone()[0]
                restored_object = connection.execute(
                    "SELECT object_id FROM CatalogueObject WHERE object_id = ?",
                    ("messier-M110",),
                ).fetchone()
            self.assertEqual(row_count, CATALOGUE_OBJECT_COUNT)
            self.assertEqual(preserved_description, "nota locale")
            self.assertIsNotNone(restored_object)

    def test_catalogue_seed_refreshes_known_builtin_text_corrections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    """
                    UPDATE CatalogueObject
                    SET tipo = ?, descrizione = ?
                    WHERE object_id = ?
                    """,
                    (
                        "Elliptical galaxy",
                        "C53 (NGC 3115) - Galassia ellittica nella costellazione "
                        "di Sestante.",
                        "caldwell-C53",
                    ),
                )
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                refreshed = connection.execute(
                    """
                    SELECT tipo, descrizione
                    FROM CatalogueObject WHERE object_id = ?
                    """,
                    ("caldwell-C53",),
                ).fetchone()
                connection.execute(
                    "UPDATE CatalogueObject SET descrizione = ? WHERE object_id = ?",
                    ("descrizione personalizzata", "caldwell-C53"),
                )
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                preserved = connection.execute(
                    """
                    SELECT tipo, descrizione
                    FROM CatalogueObject WHERE object_id = ?
                    """,
                    ("caldwell-C53",),
                ).fetchone()

            self.assertEqual(
                refreshed,
                (
                    "Lenticular galaxy",
                    "C53 (NGC 3115) - Galassia lenticolare nella costellazione "
                    "del Sestante.",
                ),
            )
            self.assertEqual(
                preserved,
                ("Lenticular galaxy", "descrizione personalizzata"),
            )

    def test_legacy_messier_table_migrates_to_generic_catalogue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    """
                    CREATE TABLE MessierObject (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        messier_id TEXT NOT NULL UNIQUE,
                        nome TEXT NOT NULL,
                        tipo TEXT NOT NULL,
                        costellazione TEXT NOT NULL,
                        magnitudine REAL,
                        ascensione_retta TEXT NOT NULL,
                        declinazione TEXT NOT NULL,
                        dimensione_apparente TEXT,
                        descrizione TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO MessierObject (
                        messier_id, nome, tipo, costellazione, magnitudine,
                        ascensione_retta, declinazione, dimensione_apparente, descrizione
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "M1",
                        "Crab Nebula",
                        "Supernova remnant",
                        "Taurus",
                        8.4,
                        "05h 34m 31.9s",
                        "+22° 00′ 52.2″",
                        "420″ × 290″",
                        "nota locale",
                    ),
                )
                connection.execute("PRAGMA user_version = 4")
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.row_factory = sqlite3.Row
                legacy_table = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'MessierObject'"
                ).fetchone()
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                row = connection.execute(
                    """
                    SELECT descrizione, max_angular_size_deg, recommended_observation_type,
                           best_filter_class, fallback_filter_class,
                           optional_color_filter_class,
                           imaging_reducer_recommended
                    FROM CatalogueObject
                    WHERE object_id = ?
                    """,
                    ("messier-M1",),
                ).fetchone()
                row_count = connection.execute("SELECT COUNT(*) FROM CatalogueObject").fetchone()[0]
                designation = connection.execute(
                    """
                    SELECT catalogue, designation, object_id
                    FROM CatalogueDesignation
                    WHERE catalogue = ? AND designation = ?
                    """,
                    ("Messier", "M1"),
                ).fetchone()

            self.assertIsNone(legacy_table)
            self.assertEqual(version, SCHEMA_VERSION)
            self.assertEqual(row_count, CATALOGUE_OBJECT_COUNT)
            self.assertEqual(row["descrizione"], "nota locale")
            self.assertEqual(row["max_angular_size_deg"], 0.117)
            self.assertEqual(row["recommended_observation_type"], "General")
            self.assertEqual(row["best_filter_class"], "UHC")
            self.assertEqual(row["fallback_filter_class"], "")
            self.assertEqual(row["optional_color_filter_class"], "")
            self.assertEqual(row["imaging_reducer_recommended"], 0)
            self.assertEqual(tuple(designation), ("Messier", "M1", "messier-M1"))
            self.assertEqual(row["recommended_observation_type"], "General")

    def test_existing_user_data_survives_update_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            database_path = runtime_dir / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)
            equipment = EquipmentCatalogRepository(database_path)
            equipment.add_profile("Profilo portabile", "preset:naked-eye", active=True)
            ObservationRepository(database_path).add("2026-06-25", "Saturno", "Roma", "", "", 5, "Test")
            preferences = LocationPreferenceStore(runtime_dir / "user_preferences.json", runtime_dir / "location_cache.json")
            preferences.update_preferences(auto_detect_location_on_startup=False)

            initialize_database(database_path, schema_path)

            equipment_after_update = EquipmentCatalogRepository(database_path)
            profile_names = [profile["profile_name"] for profile in equipment_after_update.profiles()]
            observations = ObservationRepository(database_path).list_all()
            preferences_after_update = LocationPreferenceStore(runtime_dir / "user_preferences.json", runtime_dir / "location_cache.json")
            self.assertIn("Profilo portabile", profile_names)
            self.assertTrue(any(row["object_name"] == "Saturno" for row in observations))
            self.assertFalse(preferences_after_update.preferences().auto_detect_location_on_startup)

    def test_runtime_folder_can_be_copied_with_user_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_dir = root / "NightScope"
            runtime_dir.mkdir()
            database_path = runtime_dir / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)
            EquipmentCatalogRepository(database_path).add_profile("Profilo copiato", "preset:naked-eye", active=True)
            ObservationRepository(database_path).add("2026-06-25", "M13", "Roma", "", "", 4, "Portability")
            LocationPreferenceStore(
                runtime_dir / "user_preferences.json",
                runtime_dir / "location_cache.json",
            ).update_preferences(auto_detect_location_on_startup=False)

            copied_runtime_dir = root / "NightScopeCopy"
            shutil.copytree(runtime_dir, copied_runtime_dir)
            copied_database_path = copied_runtime_dir / "nightscope.db"

            copied_profiles = EquipmentCatalogRepository(copied_database_path).profiles()
            copied_observations = ObservationRepository(copied_database_path).list_all()
            copied_preferences = LocationPreferenceStore(
                copied_runtime_dir / "user_preferences.json",
                copied_runtime_dir / "location_cache.json",
            ).preferences()
            self.assertIn("Profilo copiato", [profile["profile_name"] for profile in copied_profiles])
            self.assertTrue(any(row["object_name"] == "M13" for row in copied_observations))
            self.assertFalse(copied_preferences.auto_detect_location_on_startup)

    def test_pyinstaller_spec_does_not_package_runtime_database(self) -> None:
        spec = (Path(__file__).resolve().parents[2] / "packaging" / "NightScope.spec").read_text(encoding="utf-8")
        self.assertNotIn("nightscope.db", spec)
        self.assertIn("schema.sql", spec)
        self.assertIn("catalogue_objects_seed.csv", spec)
        self.assertIn("catalogue_designations_seed.csv", spec)
        self.assertIn("binocular_catalog_seed.csv", spec)
        self.assertIn("smart_telescope_capabilities_seed.csv", spec)
        self.assertIn("astronomy_camera_catalog_seed.csv", spec)
        self.assertIn("camera_body_catalog_seed.csv", spec)
        self.assertIn("filter_catalog_seed.csv", spec)
        self.assertIn("reducer_catalog_seed.csv", spec)
        self.assertIn("reducer_telescope_compatibility_seed.csv", spec)
        self.assertNotIn("light_pollution_seed.csv", spec)

    def test_runtime_database_path_is_portable_and_copies_legacy_database(self) -> None:
        from astro_viewer import main as main_module
        from astro_viewer.app.runtime_paths import RuntimePaths

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_paths = RuntimePaths(
                data_dir=temp_path / "data" / "NightScope",
                config_dir=temp_path / "config" / "NightScope",
                cache_dir=temp_path / "cache" / "NightScope",
                state_dir=temp_path / "state" / "NightScope",
            )
            base_dir = temp_path / "_internal" / "astro_viewer"
            legacy_data_dir = base_dir / "data"
            legacy_data_dir.mkdir(parents=True)
            legacy_database = legacy_data_dir / "nightscope.db"
            legacy_database.write_bytes(b"legacy-db")
            (legacy_data_dir / "nightscope.db.backup").write_bytes(b"legacy-backup")
            (legacy_data_dir / "user_preferences.json").write_text('{"saved": true}', encoding="utf-8")
            (legacy_data_dir / "location_cache.json").write_text('{"cached": true}', encoding="utf-8")
            (legacy_data_dir / "nasa_aod_cache.json").write_text('{"aod": true}', encoding="utf-8")

            with patch.object(
                main_module,
                "RUNTIME_PATHS",
                runtime_paths,
            ), patch.object(main_module, "BASE_DIR", base_dir):
                database_path, schema_path = main_module._database_paths()

            self.assertEqual(database_path, runtime_paths.database_path)
            self.assertEqual(schema_path, base_dir / "data" / "schema.sql")
            self.assertEqual(database_path.read_bytes(), b"legacy-db")
            self.assertEqual(
                runtime_paths.database_backup_path.read_bytes(),
                b"legacy-backup",
            )
            self.assertTrue(runtime_paths.preferences_path.exists())
            self.assertTrue(runtime_paths.location_cache_path.exists())
            self.assertTrue(runtime_paths.nasa_aod_cache_path.exists())

    def test_runtime_migration_preserves_existing_xdg_preferences(self) -> None:
        from astro_viewer import main as main_module
        from astro_viewer.app.runtime_paths import RuntimePaths

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_paths = RuntimePaths(
                data_dir=temp_path / "data" / "NightScope",
                config_dir=temp_path / "config" / "NightScope",
                cache_dir=temp_path / "cache" / "NightScope",
                state_dir=temp_path / "state" / "NightScope",
            )
            runtime_paths.database_path.parent.mkdir(parents=True)
            runtime_paths.database_path.write_bytes(b"current-db")
            runtime_paths.preferences_path.parent.mkdir(parents=True)
            runtime_paths.preferences_path.write_text(
                '{"language": "es"}',
                encoding="utf-8",
            )
            base_dir = temp_path / "_internal" / "astro_viewer"
            legacy_data_dir = base_dir / "data"
            legacy_data_dir.mkdir(parents=True)
            (legacy_data_dir / "nightscope.db").write_bytes(b"legacy-db")
            (legacy_data_dir / "user_preferences.json").write_text(
                '{"language": "it"}',
                encoding="utf-8",
            )
            (legacy_data_dir / "location_cache.json").write_text(
                '{"cached": true}',
                encoding="utf-8",
            )

            with patch.object(
                main_module,
                "RUNTIME_PATHS",
                runtime_paths,
            ), patch.object(main_module, "BASE_DIR", base_dir):
                database_path, _ = main_module._database_paths()

            self.assertEqual(database_path.read_bytes(), b"current-db")
            self.assertEqual(
                runtime_paths.preferences_path.read_text(encoding="utf-8"),
                '{"language": "es"}',
            )
            self.assertTrue(runtime_paths.location_cache_path.exists())

    def test_corrupt_database_is_quarantined_and_rebuilt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            database_path.write_text("not a sqlite database", encoding="utf-8")

            with self.assertLogs("astro_viewer.app.database.bootstrap", level="WARNING"):
                initialize_database(database_path, schema_path)

            quarantined = list(Path(temp_dir).glob("nightscope.db.corrupt-*.bak"))
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(
                len(CatalogueRepository(database_path).list_objects()),
                CATALOGUE_OBJECT_COUNT,
            )


if __name__ == "__main__":
    unittest.main()
