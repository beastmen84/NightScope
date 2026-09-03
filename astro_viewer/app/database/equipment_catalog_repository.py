"""Persist and project global equipment catalogues through SQLite.

``EquipmentProfileRepository`` is inherited only as a compatibility surface for
older internal callers.  New application code receives the profile repository
separately, while catalogue deletion reuses its transaction-scoped assignment
helpers so existing profile data remains atomic and intact.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections.abc import Iterable, Mapping
from contextlib import closing

from astro_viewer.app.database.equipment_profile_repository import (
    EquipmentProfileRepository,
    profile_usage_count,
    remove_item_from_profiles,
)

from astro_viewer.app.models.filtering import FILTER_CLASS_LABELS
from astro_viewer.app.services.equipment_taxonomy import (
    ASTRONOMY_CAMERA_CLASS_LABELS,
    CAMERA_BODY_TYPE_LABELS,
    CAMERA_SENSOR_FORMAT_LABELS,
    MOUNT_TYPE_LABELS,
    SENSOR_COLOR_MODE_LABELS,
    SENSOR_SHUTTER_LABELS,
    SENSOR_TECHNOLOGY_LABELS,
    canonical_mount_type,
    canonical_telescope_category,
    canonical_telescope_optical_type,
    mount_type_label,
    telescope_category_label,
    telescope_optical_type_code,
    telescope_optical_type_label,
)
from astro_viewer.app.services.localization import (
    format_compact_number,
    format_number,
    tr,
)

OPTICAL_SYSTEM_LABELS = {
    "SCT_CLASSIC": tr("SCT classico"),
    "EDGEHD": "EdgeHD",
    "REFRACTOR": tr("Rifrattore"),
    "RC": "Ritchey-Chrétien",
    "UNIVERSAL": tr("Universale"),
    "OTHER": tr("Altro"),
}

_SMART_CAPABILITY_COLUMNS = """
    sc.supports_optical_visual,
    sc.supports_interchangeable_eyepieces,
    sc.supports_external_cameras,
    sc.supports_external_optical_modifiers,
    sc.sensor_model,
    sc.sensor_width_mm,
    sc.sensor_height_mm,
    sc.resolution_width_px,
    sc.resolution_height_px,
    sc.pixel_size_um,
    sc.bit_depth,
    sc.color_mode,
    sc.full_resolution_fps,
    sc.supports_live_stacking,
    sc.supports_video,
    sc.supports_mosaic,
    sc.exposure_control_mode,
    sc.integrated_filter_codes,
    sc.specification_source_url
"""


def _all_finite(*values: float | None) -> bool:
    return all(value is None or math.isfinite(value) for value in values)


def _natural_sort_key(value: object) -> tuple[tuple[int, object], ...]:
    parts = re.split(r"(\d+(?:\.\d+)?)", str(value or "").casefold())
    return tuple(
        (0, float(part)) if re.fullmatch(r"\d+(?:\.\d+)?", part) else (1, part)
        for part in parts
        if part
    )


class EquipmentCatalogRepository(EquipmentProfileRepository):
    """Own global catalogues while retaining the historical profile API."""

    def brands(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT id, name FROM TelescopeBrand ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def models(self, brand_id: int | None = None) -> list[dict]:
        query = f"""
            SELECT tm.id, tb.name AS brand, tm.name, tm.instrument_category,
                   tm.optical_type, tm.aperture_mm, tm.focal_length_mm,
                   tm.focal_ratio, tm.mount_type, tm.notes, tm.is_builtin,
                   tm.seed_key, tm.is_user_modified,
                   {_SMART_CAPABILITY_COLUMNS}
            FROM TelescopeModel tm
            JOIN TelescopeBrand tb ON tb.id = tm.brand_id
            LEFT JOIN SmartTelescopeCapability sc
              ON sc.telescope_model_id = tm.id
        """
        params: tuple = ()
        if brand_id is not None and brand_id > 0:
            query += " WHERE tm.brand_id = ?"
            params = (brand_id,)
        query += " ORDER BY tb.name, tm.name"
        with closing(self._connect()) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._telescope_model(row) for row in rows]

    def model_by_catalog_id(self, catalog_id: str) -> dict | None:
        if catalog_id == "preset:naked-eye":
            return None
        with closing(self._connect()) as connection:
            if catalog_id.startswith("catalog-telescope-"):
                row = connection.execute(
                    f"""
                    SELECT tm.id, tb.name AS brand, tm.name,
                           tm.instrument_category, tm.optical_type,
                           tm.aperture_mm, tm.focal_length_mm, tm.focal_ratio,
                           tm.mount_type, tm.notes, tm.is_builtin, tm.seed_key,
                           tm.is_user_modified,
                           {_SMART_CAPABILITY_COLUMNS}
                    FROM TelescopeModel tm
                    JOIN TelescopeBrand tb ON tb.id = tm.brand_id
                    LEFT JOIN SmartTelescopeCapability sc
                      ON sc.telescope_model_id = tm.id
                    WHERE tm.id = ?
                    LIMIT 1
                    """,
                    (int(catalog_id.removeprefix("catalog-telescope-")),),
                ).fetchone()
                return self._telescope_model(row) if row else None

            parts = catalog_id.split(":", 2)
            if len(parts) != 3 or parts[0] != "catalog":
                return None
            brand, model = parts[1], parts[2]
            row = connection.execute(
                f"""
                SELECT tm.id, tb.name AS brand, tm.name,
                       tm.instrument_category, tm.optical_type,
                       tm.aperture_mm, tm.focal_length_mm, tm.focal_ratio,
                       tm.mount_type, tm.notes, tm.is_builtin, tm.seed_key,
                       tm.is_user_modified,
                       {_SMART_CAPABILITY_COLUMNS}
                FROM TelescopeModel tm
                JOIN TelescopeBrand tb ON tb.id = tm.brand_id
                LEFT JOIN SmartTelescopeCapability sc
                  ON sc.telescope_model_id = tm.id
                WHERE tb.name = ? AND tm.name = ?
                LIMIT 1
                """,
                (brand, model),
            ).fetchone()
        return self._telescope_model(row) if row else None

    def add_telescope_model(
        self,
        brand: str,
        name: str,
        optical_type: str,
        aperture_mm: int,
        focal_length_mm: int,
        mount_type: str,
        notes: str = "",
        instrument_category: str = "TRADITIONAL",
        smart_capabilities: Mapping[str, object] | None = None,
    ) -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_name = name.strip()
        if not clean_brand or not clean_name:
            return False, tr("Marca e modello sono obbligatori.")
        clean_category = canonical_telescope_category(
            instrument_category,
            preserve_unknown=False,
        )
        clean_optical_type = canonical_telescope_optical_type(optical_type)
        clean_mount_type = canonical_mount_type(mount_type, preserve_unknown=False)
        if not clean_category or not clean_optical_type or not clean_mount_type:
            return False, tr(
                "Categoria, tipo ottico e montatura sono obbligatori."
            )
        if clean_mount_type not in MOUNT_TYPE_LABELS:
            return False, tr("Tipo di montatura non valido.")
        if not _all_finite(aperture_mm, focal_length_mm) or aperture_mm <= 0 or focal_length_mm <= 0:
            return False, tr("Apertura e focale devono essere maggiori di zero.")
        capability_values, capability_error = (
            self._validated_smart_capabilities(
                clean_category,
                smart_capabilities,
            )
        )
        if capability_error:
            return False, capability_error
        with closing(self._connect()) as connection:
            brand_id = self._ensure_brand(connection, clean_brand)
            duplicate = connection.execute(
                "SELECT id FROM TelescopeModel WHERE brand_id = ? AND name = ?",
                (brand_id, clean_name),
            ).fetchone()
            if duplicate:
                return False, tr("Questo modello è già presente nel catalogo.")
            focal_ratio = round(focal_length_mm / aperture_mm, 1) if aperture_mm > 0 else None
            cursor = connection.execute(
                """
                INSERT INTO TelescopeModel (
                    brand_id, name, instrument_category, optical_type,
                    aperture_mm, focal_length_mm, focal_ratio, mount_type, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brand_id,
                    clean_name,
                    clean_category,
                    clean_optical_type,
                    aperture_mm,
                    focal_length_mm,
                    focal_ratio,
                    clean_mount_type,
                    notes.strip(),
                ),
            )
            if clean_category == "SMART_INTEGRATED":
                self._replace_smart_capabilities(
                    connection,
                    int(cursor.lastrowid),
                    capability_values,
                )
            connection.commit()
        return True, tr("Modello telescopio aggiunto.")

    def update_telescope_model(
        self,
        model_id: int,
        brand: str,
        name: str,
        optical_type: str,
        aperture_mm: int,
        focal_length_mm: int,
        mount_type: str,
        notes: str = "",
        instrument_category: str = "TRADITIONAL",
        smart_capabilities: Mapping[str, object] | None = None,
    ) -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_name = name.strip()
        if not clean_brand or not clean_name:
            return False, tr("Marca e modello sono obbligatori.")
        clean_category = canonical_telescope_category(
            instrument_category,
            preserve_unknown=False,
        )
        clean_optical_type = canonical_telescope_optical_type(optical_type)
        clean_mount_type = canonical_mount_type(mount_type, preserve_unknown=False)
        if not clean_category or not clean_optical_type or not clean_mount_type:
            return False, tr(
                "Categoria, tipo ottico e montatura sono obbligatori."
            )
        if clean_mount_type not in MOUNT_TYPE_LABELS:
            return False, tr("Tipo di montatura non valido.")
        if not _all_finite(aperture_mm, focal_length_mm) or aperture_mm <= 0 or focal_length_mm <= 0:
            return False, tr("Apertura e focale devono essere maggiori di zero.")
        capability_values, capability_error = (
            self._validated_smart_capabilities(
                clean_category,
                smart_capabilities,
            )
        )
        if capability_error:
            return False, capability_error
        with closing(self._connect()) as connection:
            old = self._telescope_model_by_id(connection, model_id)
            if not old:
                return False, tr("Modello telescopio non trovato.")
            brand_id = self._ensure_brand(connection, clean_brand)
            duplicate = connection.execute(
                "SELECT id FROM TelescopeModel WHERE brand_id = ? AND name = ? AND id <> ?",
                (brand_id, clean_name, model_id),
            ).fetchone()
            if duplicate:
                return False, tr("Questo modello è già presente nel catalogo.")
            focal_ratio = round(focal_length_mm / aperture_mm, 1) if aperture_mm > 0 else None
            connection.execute(
                """
                UPDATE TelescopeModel
                SET brand_id = ?, name = ?, instrument_category = ?,
                    optical_type = ?, aperture_mm = ?, focal_length_mm = ?,
                    focal_ratio = ?, mount_type = ?, notes = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                (
                    brand_id,
                    clean_name,
                    clean_category,
                    clean_optical_type,
                    aperture_mm,
                    focal_length_mm,
                    focal_ratio,
                    clean_mount_type,
                    notes.strip(),
                    model_id,
                ),
            )
            if clean_category == "SMART_INTEGRATED":
                if smart_capabilities is not None:
                    self._replace_smart_capabilities(
                        connection,
                        model_id,
                        capability_values,
                    )
                else:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO SmartTelescopeCapability (
                            telescope_model_id
                        )
                        VALUES (?)
                        """,
                        (model_id,),
                    )
            else:
                connection.execute(
                    """
                    DELETE FROM SmartTelescopeCapability
                    WHERE telescope_model_id = ?
                    """,
                    (model_id,),
                )
            new_id = f"catalog-telescope-{model_id}"
            profile_ids = {old["catalog_id"], old.get("legacy_catalog_id"), new_id}
            for legacy_id in profile_ids:
                if not legacy_id:
                    continue
                connection.execute(
                    "UPDATE EquipmentProfileTelescope SET telescope_id = ? WHERE telescope_id = ?",
                    (new_id, legacy_id),
                )
                connection.execute(
                    "UPDATE EquipmentProfile SET telescope_id = ? WHERE telescope_id = ?",
                    (new_id, legacy_id),
                )
            connection.commit()
        return True, tr("Modello telescopio aggiornato.")

    def delete_telescope_model(self, model_id: int, remove_from_profiles: bool = False) -> tuple[bool, str]:
        catalog_id = f"catalog-telescope-{model_id}"
        legacy_id = None
        with closing(self._connect()) as connection:
            old = self._telescope_model_by_id(connection, model_id)
            if not old:
                return False, tr("Modello telescopio non trovato.")
            if old["is_builtin"]:
                return False, tr("Gli elementi integrati non possono essere eliminati.")
            legacy_id = old.get("legacy_catalog_id")
            used = profile_usage_count(
                connection,
                "telescope",
                catalog_id,
                legacy_id,
            )
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                remove_item_from_profiles(
                    connection,
                    "telescope",
                    catalog_id,
                    legacy_id,
                )
            connection.execute("DELETE FROM TelescopeModel WHERE id = ?", (model_id,))
            connection.commit()
        return True, tr("Modello telescopio eliminato.")

    def eyepieces(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, eyepiece_type, focal_length_mm,
                       min_focal_length_mm, max_focal_length_mm,
                       apparent_field_deg, afov_min, afov_max,
                       zoom_click_positions_mm, notes, is_builtin, seed_key,
                       is_user_modified
                FROM EyepieceCatalog
                ORDER BY brand, model, focal_length_mm
                """
            ).fetchall()
        return [self._eyepiece_model(row) for row in rows]

    def add_eyepiece(
        self,
        brand: str,
        model: str,
        eyepiece_type: str,
        focal_length_mm: float,
        apparent_field_deg: float,
        min_focal_length_mm: float | None = None,
        max_focal_length_mm: float | None = None,
        afov_min: float | None = None,
        afov_max: float | None = None,
        zoom_click_positions_mm: str = "",
        notes: str = "",
    ) -> tuple[bool, str]:
        values, error = self._validated_eyepiece_values(
            brand,
            model,
            eyepiece_type,
            focal_length_mm,
            apparent_field_deg,
            min_focal_length_mm,
            max_focal_length_mm,
            afov_min,
            afov_max,
            zoom_click_positions_mm,
            notes,
        )
        if error:
            return False, error
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                """
                SELECT id FROM EyepieceCatalog
                WHERE brand = ? AND model = ? AND focal_length_mm = ?
                """,
                (values[0], values[1], values[3]),
            ).fetchone()
            if duplicate:
                return False, tr("Questo oculare è già presente nel catalogo.")
            connection.execute(
                """
                INSERT INTO EyepieceCatalog (
                    brand, model, eyepiece_type, focal_length_mm, min_focal_length_mm,
                    max_focal_length_mm, apparent_field_deg, afov_min, afov_max,
                    zoom_click_positions_mm, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.commit()
        return True, tr("Oculare aggiunto.")

    def update_eyepiece(
        self,
        eyepiece_id: int,
        brand: str,
        model: str,
        eyepiece_type: str,
        focal_length_mm: float,
        apparent_field_deg: float,
        min_focal_length_mm: float | None = None,
        max_focal_length_mm: float | None = None,
        afov_min: float | None = None,
        afov_max: float | None = None,
        zoom_click_positions_mm: str = "",
        notes: str = "",
    ) -> tuple[bool, str]:
        values, error = self._validated_eyepiece_values(
            brand,
            model,
            eyepiece_type,
            focal_length_mm,
            apparent_field_deg,
            min_focal_length_mm,
            max_focal_length_mm,
            afov_min,
            afov_max,
            zoom_click_positions_mm,
            notes,
        )
        if error:
            return False, error
        with closing(self._connect()) as connection:
            existing = connection.execute(
                """
                SELECT id, is_builtin, zoom_click_positions_mm
                FROM EyepieceCatalog
                WHERE id = ?
                """,
                (eyepiece_id,),
            ).fetchone()
            if not existing:
                return False, tr("Oculare non trovato.")
            if not values[9]:
                values = values[:9] + (
                    existing["zoom_click_positions_mm"] or "",
                    values[10],
                )
            duplicate = connection.execute(
                """
                SELECT id FROM EyepieceCatalog
                WHERE brand = ? AND model = ? AND focal_length_mm = ? AND id <> ?
                """,
                (values[0], values[1], values[3], eyepiece_id),
            ).fetchone()
            if duplicate:
                return False, tr("Questo oculare è già presente nel catalogo.")
            connection.execute(
                """
                UPDATE EyepieceCatalog
                SET brand = ?, model = ?, eyepiece_type = ?, focal_length_mm = ?,
                    min_focal_length_mm = ?, max_focal_length_mm = ?,
                    apparent_field_deg = ?, afov_min = ?, afov_max = ?,
                    zoom_click_positions_mm = ?, notes = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                values + (eyepiece_id,),
            )
            connection.commit()
        return True, tr("Oculare aggiornato.")

    def delete_eyepiece(self, eyepiece_id: int, remove_from_profiles: bool = False) -> tuple[bool, str]:
        catalog_id = f"catalog-eyepiece-{eyepiece_id}"
        with closing(self._connect()) as connection:
            if self._is_builtin(connection, "EyepieceCatalog", eyepiece_id):
                return False, tr("Gli elementi integrati non possono essere eliminati.")
            used = profile_usage_count(connection, "eyepiece", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                remove_item_from_profiles(connection, "eyepiece", catalog_id)
            connection.execute("DELETE FROM EyepieceCatalog WHERE id = ?", (eyepiece_id,))
            connection.commit()
        return True, tr("Oculare eliminato.")

    def barlows(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, multiplier, notes,
                       is_builtin, seed_key, is_user_modified
                FROM BarlowCatalog
                ORDER BY brand, model, multiplier
                """
            ).fetchall()
        return [self._barlow_model(row) for row in rows]

    def add_barlow(
        self,
        brand: str,
        model: str,
        multiplier: float,
        notes: str = "",
    ) -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, tr("Marca e modello sono obbligatori.")
        if not math.isfinite(multiplier) or multiplier <= 1:
            return False, tr("Il moltiplicatore Barlow deve essere maggiore di 1.")
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                "SELECT id FROM BarlowCatalog WHERE brand = ? AND model = ? AND multiplier = ?",
                (clean_brand, clean_model, multiplier),
            ).fetchone()
            if duplicate:
                return False, tr("Questa Barlow è già presente nel catalogo.")
            connection.execute(
                """
                INSERT INTO BarlowCatalog (brand, model, multiplier, notes)
                VALUES (?, ?, ?, ?)
                """,
                (clean_brand, clean_model, multiplier, notes.strip()),
            )
            connection.commit()
        return True, tr("Barlow aggiunta.")

    def update_barlow(
        self,
        barlow_id: int,
        brand: str,
        model: str,
        multiplier: float,
        notes: str = "",
    ) -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, tr("Marca e modello sono obbligatori.")
        if not math.isfinite(multiplier) or multiplier <= 1:
            return False, tr("Il moltiplicatore Barlow deve essere maggiore di 1.")
        with closing(self._connect()) as connection:
            existing = connection.execute(
                "SELECT id, is_builtin FROM BarlowCatalog WHERE id = ?",
                (barlow_id,),
            ).fetchone()
            if not existing:
                return False, tr("Barlow non trovata.")
            duplicate = connection.execute(
                """
                SELECT id FROM BarlowCatalog
                WHERE brand = ? AND model = ? AND multiplier = ? AND id <> ?
                """,
                (clean_brand, clean_model, multiplier, barlow_id),
            ).fetchone()
            if duplicate:
                return False, tr("Questa Barlow è già presente nel catalogo.")
            connection.execute(
                """
                UPDATE BarlowCatalog
                SET brand = ?, model = ?, multiplier = ?, notes = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                (
                    clean_brand,
                    clean_model,
                    multiplier,
                    notes.strip(),
                    barlow_id,
                ),
            )
            connection.commit()
        return True, tr("Barlow aggiornata.")

    def delete_barlow(self, barlow_id: int, remove_from_profiles: bool = False) -> tuple[bool, str]:
        catalog_id = f"catalog-barlow-{barlow_id}"
        with closing(self._connect()) as connection:
            if self._is_builtin(connection, "BarlowCatalog", barlow_id):
                return False, tr("Gli elementi integrati non possono essere eliminati.")
            used = profile_usage_count(connection, "barlow", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                remove_item_from_profiles(connection, "barlow", catalog_id)
            connection.execute("DELETE FROM BarlowCatalog WHERE id = ?", (barlow_id,))
            connection.commit()
        return True, tr("Barlow eliminata.")

    def binoculars(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, magnification, objective_diameter_mm,
                       image_stabilized, is_builtin, seed_key, is_user_modified
                FROM BinocularCatalog
                """
            ).fetchall()
        models = [self._binocular_model(row) for row in rows]
        return sorted(
            models,
            key=lambda item: (
                _natural_sort_key(item["brand"]),
                _natural_sort_key(item["model"]),
                item["magnification"],
                item["objective_diameter_mm"],
                item["id"],
            ),
        )

    def add_binocular(
        self,
        brand: str,
        model: str,
        magnification: int,
        objective_diameter_mm: int,
        image_stabilized: bool = False,
    ) -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, tr("Marca e modello sono obbligatori.")
        if not _all_finite(magnification, objective_diameter_mm) or magnification <= 0 or objective_diameter_mm <= 0:
            return False, tr("Ingrandimento e diametro obiettivo devono essere maggiori di zero.")
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                """
                SELECT id FROM BinocularCatalog
                WHERE brand = ? AND model = ? AND magnification = ? AND objective_diameter_mm = ?
                """,
                (clean_brand, clean_model, magnification, objective_diameter_mm),
            ).fetchone()
            if duplicate:
                return False, tr("Questo binocolo è già presente nel catalogo.")
            connection.execute(
                """
                INSERT INTO BinocularCatalog (
                    brand, model, magnification, objective_diameter_mm, image_stabilized
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    clean_brand,
                    clean_model,
                    magnification,
                    objective_diameter_mm,
                    1 if image_stabilized else 0,
                ),
            )
            connection.commit()
        return True, tr("Binocolo aggiunto.")

    def update_binocular(
        self,
        binocular_id: int,
        brand: str,
        model: str,
        magnification: int,
        objective_diameter_mm: int,
        image_stabilized: bool = False,
    ) -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, tr("Marca e modello sono obbligatori.")
        if not _all_finite(magnification, objective_diameter_mm) or magnification <= 0 or objective_diameter_mm <= 0:
            return False, tr("Ingrandimento e diametro obiettivo devono essere maggiori di zero.")
        with closing(self._connect()) as connection:
            existing = connection.execute(
                "SELECT id, is_builtin FROM BinocularCatalog WHERE id = ?",
                (binocular_id,),
            ).fetchone()
            if not existing:
                return False, tr("Binocolo non trovato.")
            duplicate = connection.execute(
                """
                SELECT id FROM BinocularCatalog
                WHERE brand = ? AND model = ? AND magnification = ? AND objective_diameter_mm = ? AND id <> ?
                """,
                (clean_brand, clean_model, magnification, objective_diameter_mm, binocular_id),
            ).fetchone()
            if duplicate:
                return False, tr("Questo binocolo è già presente nel catalogo.")
            connection.execute(
                """
                UPDATE BinocularCatalog
                SET brand = ?, model = ?, magnification = ?, objective_diameter_mm = ?,
                    image_stabilized = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                (
                    clean_brand,
                    clean_model,
                    magnification,
                    objective_diameter_mm,
                    1 if image_stabilized else 0,
                    binocular_id,
                ),
            )
            connection.commit()
        return True, tr("Binocolo aggiornato.")

    def delete_binocular(
        self,
        binocular_id: int,
        remove_from_profiles: bool = False,
    ) -> tuple[bool, str]:
        catalog_id = f"catalog-binocular-{binocular_id}"
        with closing(self._connect()) as connection:
            existing = connection.execute(
                "SELECT id, is_builtin FROM BinocularCatalog WHERE id = ?",
                (binocular_id,),
            ).fetchone()
            if not existing:
                return False, tr("Binocolo non trovato.")
            if bool(existing["is_builtin"]):
                return False, tr("Gli elementi integrati non possono essere eliminati.")
            used = profile_usage_count(connection, "binocular", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                remove_item_from_profiles(connection, "binocular", catalog_id)
            connection.execute("DELETE FROM BinocularCatalog WHERE id = ?", (binocular_id,))
            connection.commit()
        return True, tr("Binocolo eliminato.")

    def astronomy_cameras(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, camera_class, sensor_model,
                       sensor_technology, color_mode, sensor_width_mm,
                       sensor_height_mm, resolution_width_px,
                       resolution_height_px, pixel_size_um, bit_depth,
                       max_fps, cooled, cooling_delta_c, shutter_type,
                       backfocus_mm, source_url, is_builtin, seed_key,
                       is_user_modified
                FROM AstronomyCameraCatalog
                ORDER BY brand, model
                """
            ).fetchall()
        return [self._astronomy_camera_model(row) for row in rows]

    def add_astronomy_camera(
        self,
        brand: str,
        model: str,
        camera_class: str,
        sensor_model: str,
        sensor_technology: str,
        color_mode: str,
        sensor_width_mm: float,
        sensor_height_mm: float,
        resolution_width_px: int,
        resolution_height_px: int,
        pixel_size_um: float,
        bit_depth: int,
        max_fps: float | None,
        cooled: bool,
        cooling_delta_c: float | None,
        shutter_type: str,
        backfocus_mm: float | None,
        source_url: str = "",
    ) -> tuple[bool, str]:
        values, error = self._validated_astronomy_camera_values(
            brand,
            model,
            camera_class,
            sensor_model,
            sensor_technology,
            color_mode,
            sensor_width_mm,
            sensor_height_mm,
            resolution_width_px,
            resolution_height_px,
            pixel_size_um,
            bit_depth,
            max_fps,
            cooled,
            cooling_delta_c,
            shutter_type,
            backfocus_mm,
            source_url,
        )
        if error:
            return False, error
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                """
                SELECT id FROM AstronomyCameraCatalog
                WHERE brand = ? AND model = ?
                """,
                values[:2],
            ).fetchone()
            if duplicate:
                return False, tr("Questa camera astronomica è già presente nel catalogo.")
            connection.execute(
                """
                INSERT INTO AstronomyCameraCatalog (
                    brand, model, camera_class, sensor_model,
                    sensor_technology, color_mode, sensor_width_mm,
                    sensor_height_mm, resolution_width_px,
                    resolution_height_px, pixel_size_um, bit_depth, max_fps,
                    cooled, cooling_delta_c, shutter_type, backfocus_mm,
                    source_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.commit()
        return True, tr("Camera astronomica aggiunta.")

    def update_astronomy_camera(
        self,
        camera_id: int,
        brand: str,
        model: str,
        camera_class: str,
        sensor_model: str,
        sensor_technology: str,
        color_mode: str,
        sensor_width_mm: float,
        sensor_height_mm: float,
        resolution_width_px: int,
        resolution_height_px: int,
        pixel_size_um: float,
        bit_depth: int,
        max_fps: float | None,
        cooled: bool,
        cooling_delta_c: float | None,
        shutter_type: str,
        backfocus_mm: float | None,
        source_url: str = "",
    ) -> tuple[bool, str]:
        values, error = self._validated_astronomy_camera_values(
            brand,
            model,
            camera_class,
            sensor_model,
            sensor_technology,
            color_mode,
            sensor_width_mm,
            sensor_height_mm,
            resolution_width_px,
            resolution_height_px,
            pixel_size_um,
            bit_depth,
            max_fps,
            cooled,
            cooling_delta_c,
            shutter_type,
            backfocus_mm,
            source_url,
        )
        if error:
            return False, error
        with closing(self._connect()) as connection:
            existing = connection.execute(
                "SELECT id FROM AstronomyCameraCatalog WHERE id = ?",
                (camera_id,),
            ).fetchone()
            if not existing:
                return False, tr("Camera astronomica non trovata.")
            duplicate = connection.execute(
                """
                SELECT id FROM AstronomyCameraCatalog
                WHERE brand = ? AND model = ? AND id <> ?
                """,
                values[:2] + (camera_id,),
            ).fetchone()
            if duplicate:
                return False, tr("Questa camera astronomica è già presente nel catalogo.")
            connection.execute(
                """
                UPDATE AstronomyCameraCatalog
                SET brand = ?, model = ?, camera_class = ?, sensor_model = ?,
                    sensor_technology = ?, color_mode = ?,
                    sensor_width_mm = ?, sensor_height_mm = ?,
                    resolution_width_px = ?, resolution_height_px = ?,
                    pixel_size_um = ?, bit_depth = ?, max_fps = ?, cooled = ?,
                    cooling_delta_c = ?, shutter_type = ?, backfocus_mm = ?,
                    source_url = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                values + (camera_id,),
            )
            connection.commit()
        return True, tr("Camera astronomica aggiornata.")

    def delete_astronomy_camera(
        self,
        camera_id: int,
        remove_from_profiles: bool = False,
    ) -> tuple[bool, str]:
        with closing(self._connect()) as connection:
            existing = connection.execute(
                """
                SELECT id, is_builtin
                FROM AstronomyCameraCatalog
                WHERE id = ?
                """,
                (camera_id,),
            ).fetchone()
            if not existing:
                return False, tr("Camera astronomica non trovata.")
            if bool(existing["is_builtin"]):
                return False, tr("Gli elementi integrati non possono essere eliminati.")
            catalog_id = f"catalog-astronomy-camera-{camera_id}"
            used = profile_usage_count(
                connection,
                "astronomy_camera",
                catalog_id,
            )
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                remove_item_from_profiles(
                    connection,
                    "astronomy_camera",
                    catalog_id,
                )
            connection.execute(
                "DELETE FROM AstronomyCameraCatalog WHERE id = ?",
                (camera_id,),
            )
            connection.commit()
        return True, tr("Camera astronomica eliminata.")

    def camera_bodies(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, body_type, sensor_format, lens_mount,
                       sensor_width_mm, sensor_height_mm, resolution_width_px,
                       resolution_height_px, raw_bit_depth,
                       max_video_width_px, max_video_height_px,
                       max_video_fps, live_view, bulb_mode, source_url,
                       is_builtin, seed_key, is_user_modified
                FROM CameraBodyCatalog
                ORDER BY brand, model
                """
            ).fetchall()
        return [self._camera_body_model(row) for row in rows]

    def add_camera_body(
        self,
        brand: str,
        model: str,
        body_type: str,
        sensor_format: str,
        lens_mount: str,
        sensor_width_mm: float,
        sensor_height_mm: float,
        resolution_width_px: int,
        resolution_height_px: int,
        raw_bit_depth: int,
        max_video_width_px: int | None,
        max_video_height_px: int | None,
        max_video_fps: float | None,
        live_view: bool,
        bulb_mode: bool,
        source_url: str = "",
    ) -> tuple[bool, str]:
        values, error = self._validated_camera_body_values(
            brand,
            model,
            body_type,
            sensor_format,
            lens_mount,
            sensor_width_mm,
            sensor_height_mm,
            resolution_width_px,
            resolution_height_px,
            raw_bit_depth,
            max_video_width_px,
            max_video_height_px,
            max_video_fps,
            live_view,
            bulb_mode,
            source_url,
        )
        if error:
            return False, error
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                """
                SELECT id FROM CameraBodyCatalog
                WHERE brand = ? AND model = ?
                """,
                values[:2],
            ).fetchone()
            if duplicate:
                return False, tr("Questo corpo macchina è già presente nel catalogo.")
            connection.execute(
                """
                INSERT INTO CameraBodyCatalog (
                    brand, model, body_type, sensor_format, lens_mount,
                    sensor_width_mm, sensor_height_mm, resolution_width_px,
                    resolution_height_px, raw_bit_depth, max_video_width_px,
                    max_video_height_px, max_video_fps, live_view, bulb_mode,
                    source_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.commit()
        return True, tr("Corpo macchina aggiunto.")

    def update_camera_body(
        self,
        camera_id: int,
        brand: str,
        model: str,
        body_type: str,
        sensor_format: str,
        lens_mount: str,
        sensor_width_mm: float,
        sensor_height_mm: float,
        resolution_width_px: int,
        resolution_height_px: int,
        raw_bit_depth: int,
        max_video_width_px: int | None,
        max_video_height_px: int | None,
        max_video_fps: float | None,
        live_view: bool,
        bulb_mode: bool,
        source_url: str = "",
    ) -> tuple[bool, str]:
        values, error = self._validated_camera_body_values(
            brand,
            model,
            body_type,
            sensor_format,
            lens_mount,
            sensor_width_mm,
            sensor_height_mm,
            resolution_width_px,
            resolution_height_px,
            raw_bit_depth,
            max_video_width_px,
            max_video_height_px,
            max_video_fps,
            live_view,
            bulb_mode,
            source_url,
        )
        if error:
            return False, error
        with closing(self._connect()) as connection:
            existing = connection.execute(
                "SELECT id FROM CameraBodyCatalog WHERE id = ?",
                (camera_id,),
            ).fetchone()
            if not existing:
                return False, tr("Corpo macchina non trovato.")
            duplicate = connection.execute(
                """
                SELECT id FROM CameraBodyCatalog
                WHERE brand = ? AND model = ? AND id <> ?
                """,
                values[:2] + (camera_id,),
            ).fetchone()
            if duplicate:
                return False, tr("Questo corpo macchina è già presente nel catalogo.")
            connection.execute(
                """
                UPDATE CameraBodyCatalog
                SET brand = ?, model = ?, body_type = ?, sensor_format = ?,
                    lens_mount = ?, sensor_width_mm = ?,
                    sensor_height_mm = ?, resolution_width_px = ?,
                    resolution_height_px = ?, raw_bit_depth = ?,
                    max_video_width_px = ?, max_video_height_px = ?,
                    max_video_fps = ?, live_view = ?, bulb_mode = ?,
                    source_url = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                values + (camera_id,),
            )
            connection.commit()
        return True, tr("Corpo macchina aggiornato.")

    def delete_camera_body(
        self,
        camera_id: int,
        remove_from_profiles: bool = False,
    ) -> tuple[bool, str]:
        with closing(self._connect()) as connection:
            existing = connection.execute(
                """
                SELECT id, is_builtin
                FROM CameraBodyCatalog
                WHERE id = ?
                """,
                (camera_id,),
            ).fetchone()
            if not existing:
                return False, tr("Corpo macchina non trovato.")
            if bool(existing["is_builtin"]):
                return False, tr("Gli elementi integrati non possono essere eliminati.")
            catalog_id = f"catalog-camera-body-{camera_id}"
            used = profile_usage_count(
                connection,
                "camera_body",
                catalog_id,
            )
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                remove_item_from_profiles(
                    connection,
                    "camera_body",
                    catalog_id,
                )
            connection.execute(
                "DELETE FROM CameraBodyCatalog WHERE id = ?",
                (camera_id,),
            )
            connection.commit()
        return True, tr("Corpo macchina eliminato.")

    def filters(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, filter_class,
                       central_wavelength_nm, bandwidth_nm, transmission_pct,
                       minimum_aperture_mm, notes, is_builtin, seed_key,
                       is_user_modified
                FROM FilterCatalog
                ORDER BY brand, model
                """
            ).fetchall()
        return [self._filter_model(row) for row in rows]

    def add_filter(
        self,
        brand: str,
        model: str,
        filter_class: str,
        central_wavelength_nm: float | None = None,
        bandwidth_nm: float | None = None,
        transmission_pct: float | None = None,
        minimum_aperture_mm: int | None = None,
        notes: str = "",
    ) -> tuple[bool, str]:
        values, error = self._validated_filter_values(
            brand,
            model,
            filter_class,
            central_wavelength_nm,
            bandwidth_nm,
            transmission_pct,
            minimum_aperture_mm,
            notes,
        )
        if error:
            return False, error
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                """
                SELECT id FROM FilterCatalog
                WHERE brand = ? AND model = ?
                """,
                values[:2],
            ).fetchone()
            if duplicate:
                return False, tr("Questo filtro è già presente nel catalogo.")
            connection.execute(
                """
                INSERT INTO FilterCatalog (
                    brand, model, filter_class,
                    central_wavelength_nm, bandwidth_nm, transmission_pct,
                    minimum_aperture_mm, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.commit()
        return True, tr("Filtro aggiunto.")

    def update_filter(
        self,
        filter_id: int,
        brand: str,
        model: str,
        filter_class: str,
        central_wavelength_nm: float | None = None,
        bandwidth_nm: float | None = None,
        transmission_pct: float | None = None,
        minimum_aperture_mm: int | None = None,
        notes: str = "",
    ) -> tuple[bool, str]:
        values, error = self._validated_filter_values(
            brand,
            model,
            filter_class,
            central_wavelength_nm,
            bandwidth_nm,
            transmission_pct,
            minimum_aperture_mm,
            notes,
        )
        if error:
            return False, error
        with closing(self._connect()) as connection:
            existing = connection.execute(
                "SELECT id, is_builtin FROM FilterCatalog WHERE id = ?",
                (filter_id,),
            ).fetchone()
            if not existing:
                return False, tr("Filtro non trovato.")
            duplicate = connection.execute(
                """
                SELECT id FROM FilterCatalog
                WHERE brand = ? AND model = ? AND id <> ?
                """,
                values[:2] + (filter_id,),
            ).fetchone()
            if duplicate:
                return False, tr("Questo filtro è già presente nel catalogo.")
            connection.execute(
                """
                UPDATE FilterCatalog
                SET brand = ?, model = ?, filter_class = ?,
                    central_wavelength_nm = ?, bandwidth_nm = ?,
                    transmission_pct = ?, minimum_aperture_mm = ?, notes = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                values + (filter_id,),
            )
            connection.commit()
        return True, tr("Filtro aggiornato.")

    def delete_filter(
        self,
        filter_id: int,
        remove_from_profiles: bool = False,
    ) -> tuple[bool, str]:
        catalog_id = f"catalog-filter-{filter_id}"
        with closing(self._connect()) as connection:
            if self._is_builtin(connection, "FilterCatalog", filter_id):
                return False, tr("Gli elementi integrati non possono essere eliminati.")
            existing = connection.execute(
                "SELECT id FROM FilterCatalog WHERE id = ?",
                (filter_id,),
            ).fetchone()
            if not existing:
                return False, tr("Filtro non trovato.")
            used = profile_usage_count(connection, "filter", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                remove_item_from_profiles(connection, "filter", catalog_id)
            connection.execute("DELETE FROM FilterCatalog WHERE id = ?", (filter_id,))
            connection.commit()
        return True, tr("Filtro eliminato.")

    def reducers(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, reduction_factor, optical_system,
                       connection, backfocus_mm,
                       visual_compatible, imaging_compatible, corrected_field,
                       notes, is_builtin, seed_key, is_user_modified
                FROM ReducerCatalog
                ORDER BY brand, model, reduction_factor
                """
            ).fetchall()
            compatibility_rows = connection.execute(
                """
                SELECT compatibility.reducer_id, model.id AS telescope_model_id,
                       brand.name AS telescope_brand, model.name AS telescope_model
                FROM ReducerTelescopeCompatibility compatibility
                JOIN TelescopeModel model ON model.id = compatibility.telescope_model_id
                JOIN TelescopeBrand brand ON brand.id = model.brand_id
                ORDER BY brand.name, model.name
                """
            ).fetchall()
        compatibility_by_reducer: dict[int, list[dict]] = {}
        for row in compatibility_rows:
            compatibility_by_reducer.setdefault(int(row["reducer_id"]), []).append(
                {
                    "catalog_id": f"catalog-telescope-{row['telescope_model_id']}",
                    "brand": str(row["telescope_brand"]),
                    "model": str(row["telescope_model"]),
                    "display_name": f"{row['telescope_brand']} {row['telescope_model']}",
                }
            )
        reducers = []
        for row in rows:
            reducer = self._reducer_model(row)
            compatibility = compatibility_by_reducer.get(int(row["id"]), [])
            reducer["compatible_telescopes"] = compatibility
            reducer["compatible_telescope_ids"] = [
                item["catalog_id"] for item in compatibility
            ]
            reducer["compatibility_configured"] = bool(compatibility)
            reducers.append(reducer)
        return reducers

    def add_reducer(
        self,
        brand: str,
        model: str,
        reduction_factor: float,
        optical_system: str,
        connection_name: str = "",
        backfocus_mm: float | None = None,
        visual_compatible: bool = False,
        imaging_compatible: bool = True,
        corrected_field: bool = False,
        notes: str = "",
        compatible_telescope_ids: Iterable[str] = (),
    ) -> tuple[bool, str]:
        values, error = self._validated_reducer_values(
            brand,
            model,
            reduction_factor,
            optical_system,
            connection_name,
            backfocus_mm,
            visual_compatible,
            imaging_compatible,
            corrected_field,
            notes,
        )
        if error:
            return False, error
        with closing(self._connect()) as connection:
            telescope_model_ids, compatibility_error = (
                self._validated_reducer_telescope_ids(
                    connection,
                    compatible_telescope_ids,
                )
            )
            if compatibility_error:
                return False, compatibility_error
            duplicate = connection.execute(
                """
                SELECT id FROM ReducerCatalog
                WHERE brand = ? AND model = ? AND reduction_factor = ?
                """,
                values[:3],
            ).fetchone()
            if duplicate:
                return False, tr("Questo riduttore è già presente nel catalogo.")
            cursor = connection.execute(
                """
                INSERT INTO ReducerCatalog (
                    brand, model, reduction_factor, optical_system,
                    connection, backfocus_mm,
                    visual_compatible, imaging_compatible, corrected_field,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            self._replace_reducer_telescope_compatibility(
                connection,
                int(cursor.lastrowid),
                telescope_model_ids,
            )
            connection.commit()
        return True, tr("Riduttore aggiunto.")

    def update_reducer(
        self,
        reducer_id: int,
        brand: str,
        model: str,
        reduction_factor: float,
        optical_system: str,
        connection_name: str = "",
        backfocus_mm: float | None = None,
        visual_compatible: bool = False,
        imaging_compatible: bool = True,
        corrected_field: bool = False,
        notes: str = "",
        compatible_telescope_ids: Iterable[str] | None = None,
    ) -> tuple[bool, str]:
        with closing(self._connect()) as connection:
            existing = connection.execute(
                "SELECT id, is_builtin FROM ReducerCatalog WHERE id = ?",
                (reducer_id,),
            ).fetchone()
            if not existing:
                return False, tr("Riduttore non trovato.")
            values, error = self._validated_reducer_values(
                brand,
                model,
                reduction_factor,
                optical_system,
                connection_name,
                backfocus_mm,
                visual_compatible,
                imaging_compatible,
                corrected_field,
                notes,
            )
            if error:
                return False, error
            telescope_model_ids: tuple[int, ...] | None = None
            if compatible_telescope_ids is not None:
                telescope_model_ids, compatibility_error = self._validated_reducer_telescope_ids(
                    connection,
                    compatible_telescope_ids,
                )
                if compatibility_error:
                    return False, compatibility_error
            duplicate = connection.execute(
                """
                SELECT id FROM ReducerCatalog
                WHERE brand = ? AND model = ? AND reduction_factor = ? AND id <> ?
                """,
                values[:3] + (reducer_id,),
            ).fetchone()
            if duplicate:
                return False, tr("Questo riduttore è già presente nel catalogo.")
            connection.execute(
                """
                UPDATE ReducerCatalog
                SET brand = ?, model = ?, reduction_factor = ?,
                    optical_system = ?, connection = ?,
                    backfocus_mm = ?, visual_compatible = ?,
                    imaging_compatible = ?, corrected_field = ?, notes = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                values + (reducer_id,),
            )
            if telescope_model_ids is not None:
                self._replace_reducer_telescope_compatibility(
                    connection,
                    reducer_id,
                    telescope_model_ids,
                )
            connection.commit()
        return True, tr("Riduttore aggiornato.")

    def delete_reducer(
        self,
        reducer_id: int,
        remove_from_profiles: bool = False,
    ) -> tuple[bool, str]:
        catalog_id = f"catalog-reducer-{reducer_id}"
        with closing(self._connect()) as connection:
            if self._is_builtin(connection, "ReducerCatalog", reducer_id):
                return False, tr("Gli elementi integrati non possono essere eliminati.")
            existing = connection.execute(
                "SELECT id FROM ReducerCatalog WHERE id = ?",
                (reducer_id,),
            ).fetchone()
            if not existing:
                return False, tr("Riduttore non trovato.")
            used = profile_usage_count(connection, "reducer", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                remove_item_from_profiles(connection, "reducer", catalog_id)
            connection.execute("DELETE FROM ReducerCatalog WHERE id = ?", (reducer_id,))
            connection.commit()
        return True, tr("Riduttore eliminato.")

    @staticmethod
    def _telescope_model(row: sqlite3.Row) -> dict:
        instrument_category = canonical_telescope_category(
            row["instrument_category"]
        )
        smart_integrated = instrument_category == "SMART_INTEGRATED"
        filter_codes = tuple(
            code
            for code in str(
                row["integrated_filter_codes"] or ""
            ).split(";")
            if code
        )
        smart_capabilities = {
            "supports_optical_visual": (
                bool(row["supports_optical_visual"])
                if smart_integrated
                else True
            ),
            "supports_interchangeable_eyepieces": (
                bool(row["supports_interchangeable_eyepieces"])
                if smart_integrated
                else True
            ),
            "supports_external_cameras": (
                bool(row["supports_external_cameras"])
                if smart_integrated
                else True
            ),
            "supports_external_optical_modifiers": (
                bool(row["supports_external_optical_modifiers"])
                if smart_integrated
                else True
            ),
            "sensor_model": row["sensor_model"] or "",
            "sensor_width_mm": row["sensor_width_mm"],
            "sensor_height_mm": row["sensor_height_mm"],
            "resolution_width_px": row["resolution_width_px"],
            "resolution_height_px": row["resolution_height_px"],
            "pixel_size_um": row["pixel_size_um"],
            "bit_depth": row["bit_depth"],
            "color_mode": row["color_mode"] or "",
            "full_resolution_fps": row["full_resolution_fps"],
            "supports_live_stacking": bool(
                row["supports_live_stacking"]
            ),
            "supports_video": bool(row["supports_video"]),
            "supports_mosaic": bool(row["supports_mosaic"]),
            "exposure_control_mode": (
                row["exposure_control_mode"] or "DEVICE_MANAGED"
            ),
            "integrated_filter_codes": filter_codes,
            "specification_source_url": (
                row["specification_source_url"] or ""
            ),
        }
        return {
            "id": row["id"],
            "brand": row["brand"],
            "name": row["name"],
            "display_name": f"{row['brand']} {row['name']}",
            "instrument_category": instrument_category,
            "instrument_category_label": telescope_category_label(
                row["instrument_category"]
            ),
            "optical_type": row["optical_type"],
            "optical_type_code": telescope_optical_type_code(
                row["optical_type"]
            ),
            "optical_type_label": telescope_optical_type_label(
                row["optical_type"]
            ),
            "aperture_mm": row["aperture_mm"],
            "focal_length_mm": row["focal_length_mm"],
            "focal_ratio": row["focal_ratio"],
            "aperture_label": tr(
                "{value} mm", value=format_number(row["aperture_mm"])
            ),
            "focal_length_label": tr(
                "{value} mm", value=format_number(row["focal_length_mm"])
            ),
            "focal_ratio_label": (
                tr(
                    "f/{value}",
                    value=format_compact_number(row["focal_ratio"]),
                )
                if row["focal_ratio"] is not None
                else ""
            ),
            "mount_type": canonical_mount_type(row["mount_type"]),
            "mount_type_label": mount_type_label(row["mount_type"]),
            "notes": row["notes"] or "",
            "is_builtin": bool(row["is_builtin"]),
            "seed_key": row["seed_key"] or "",
            "is_user_modified": bool(row["is_user_modified"]),
            "catalog_id": f"catalog-telescope-{row['id']}",
            "legacy_catalog_id": f"catalog:{row['brand']}:{row['name']}",
            "smart_capabilities": smart_capabilities,
            **smart_capabilities,
        }

    @staticmethod
    def _eyepiece_model(row: sqlite3.Row) -> dict:
        eyepiece_type = row["eyepiece_type"] or "Fixed"
        min_focal = row["min_focal_length_mm"]
        max_focal = row["max_focal_length_mm"]
        focal_range = (
            tr(
                "{minimum}-{maximum} mm",
                minimum=format_compact_number(min_focal),
                maximum=format_compact_number(max_focal),
            )
            if eyepiece_type == "Zoom" and min_focal and max_focal
            else tr(
                "{value} mm",
                value=format_compact_number(row["focal_length_mm"]),
            )
        )
        return {
            "id": row["id"],
            "catalog_id": f"catalog-eyepiece-{row['id']}",
            "brand": row["brand"],
            "model": row["model"],
            "display_name": f"{row['brand']} {row['model']}",
            "eyepiece_type": eyepiece_type,
            "type": eyepiece_type,
            "type_label": tr("Zoom") if eyepiece_type == "Zoom" else tr("Fisso"),
            "focal_length_mm": row["focal_length_mm"],
            "min_focal_length_mm": min_focal,
            "max_focal_length_mm": max_focal,
            "apparent_field_deg": row["apparent_field_deg"],
            "apparent_field_label": tr(
                "{value}°",
                value=format_compact_number(row["apparent_field_deg"]),
            ),
            "afov_min": row["afov_min"],
            "afov_max": row["afov_max"],
            "zoom_click_positions_mm": row["zoom_click_positions_mm"] or "",
            "notes": row["notes"] or "",
            "focalRangeLabel": focal_range,
            "is_builtin": bool(row["is_builtin"]),
            "seed_key": row["seed_key"] or "",
            "is_user_modified": bool(row["is_user_modified"]),
        }

    @staticmethod
    def _barlow_model(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "catalog_id": f"catalog-barlow-{row['id']}",
            "brand": row["brand"],
            "model": row["model"],
            "display_name": f"{row['brand']} {row['model']}",
            "multiplier": row["multiplier"],
            "multiplier_label": tr(
                "{value}x", value=format_compact_number(row["multiplier"])
            ),
            "notes": row["notes"] or "",
            "is_builtin": bool(row["is_builtin"]),
            "seed_key": row["seed_key"] or "",
            "is_user_modified": bool(row["is_user_modified"]),
        }

    @staticmethod
    def _binocular_model(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "catalog_id": f"catalog-binocular-{row['id']}",
            "brand": row["brand"],
            "model": row["model"],
            "display_name": f"{row['brand']} {row['model']}",
            "magnification": row["magnification"],
            "objective_diameter_mm": row["objective_diameter_mm"],
            "image_stabilized": bool(row["image_stabilized"]),
            "spec_label": f"{row['magnification']}×{row['objective_diameter_mm']}",
            "is_builtin": bool(row["is_builtin"]),
            "seed_key": row["seed_key"] or "",
            "is_user_modified": bool(row["is_user_modified"]),
        }

    @staticmethod
    def _astronomy_camera_model(row: sqlite3.Row) -> dict:
        camera_class = str(row["camera_class"] or "").strip().upper()
        sensor_technology = str(row["sensor_technology"] or "").strip().upper()
        color_mode = str(row["color_mode"] or "").strip().upper()
        shutter_type = str(row["shutter_type"] or "").strip().upper()
        cooled = bool(row["cooled"])
        cooling_delta = row["cooling_delta_c"]
        return {
            "id": row["id"],
            "catalog_id": f"catalog-astronomy-camera-{row['id']}",
            "brand": row["brand"],
            "model": row["model"],
            "display_name": f"{row['brand']} {row['model']}",
            "camera_class": camera_class,
            "camera_class_label": ASTRONOMY_CAMERA_CLASS_LABELS.get(
                camera_class,
                camera_class,
            ),
            "sensor_model": row["sensor_model"],
            "sensor_technology": sensor_technology,
            "sensor_technology_label": SENSOR_TECHNOLOGY_LABELS.get(
                sensor_technology,
                sensor_technology,
            ),
            "color_mode": color_mode,
            "color_mode_label": SENSOR_COLOR_MODE_LABELS.get(
                color_mode,
                color_mode,
            ),
            "sensor_width_mm": row["sensor_width_mm"],
            "sensor_height_mm": row["sensor_height_mm"],
            "sensor_size_label": tr(
                "{width} × {height} mm",
                width=format_compact_number(row["sensor_width_mm"]),
                height=format_compact_number(row["sensor_height_mm"]),
            ),
            "resolution_width_px": row["resolution_width_px"],
            "resolution_height_px": row["resolution_height_px"],
            "resolution_label": tr(
                "{width} × {height} px",
                width=format_number(row["resolution_width_px"]),
                height=format_number(row["resolution_height_px"]),
            ),
            "pixel_size_um": row["pixel_size_um"],
            "pixel_size_label": tr(
                "{value} µm",
                value=format_compact_number(row["pixel_size_um"]),
            ),
            "bit_depth": row["bit_depth"],
            "bit_depth_label": tr(
                "{value} bit",
                value=format_number(row["bit_depth"]),
            ),
            "max_fps": row["max_fps"],
            "max_fps_label": (
                tr(
                    "{value} fps",
                    value=format_compact_number(row["max_fps"]),
                )
                if row["max_fps"] is not None
                else ""
            ),
            "cooled": cooled,
            "cooling_delta_c": cooling_delta,
            "cooling_label": (
                tr(
                    "Raffreddata (ΔT {value} °C)",
                    value=format_compact_number(cooling_delta),
                )
                if cooled and cooling_delta is not None
                else tr("Raffreddata")
                if cooled
                else tr("Non raffreddata")
            ),
            "shutter_type": shutter_type,
            "shutter_type_label": SENSOR_SHUTTER_LABELS.get(
                shutter_type,
                shutter_type,
            ),
            "backfocus_mm": row["backfocus_mm"],
            "backfocus_label": (
                tr(
                    "Backfocus {value} mm",
                    value=format_compact_number(row["backfocus_mm"]),
                )
                if row["backfocus_mm"] is not None
                else ""
            ),
            "source_url": row["source_url"] or "",
            "is_builtin": bool(row["is_builtin"]),
            "seed_key": row["seed_key"] or "",
            "is_user_modified": bool(row["is_user_modified"]),
        }

    @staticmethod
    def _camera_body_model(row: sqlite3.Row) -> dict:
        body_type = str(row["body_type"] or "").strip().upper()
        sensor_format = str(row["sensor_format"] or "").strip().upper()
        pixel_width_um = (
            float(row["sensor_width_mm"]) * 1000.0
            / int(row["resolution_width_px"])
        )
        pixel_height_um = (
            float(row["sensor_height_mm"]) * 1000.0
            / int(row["resolution_height_px"])
        )
        pixel_size_um = round((pixel_width_um + pixel_height_um) / 2.0, 3)
        video_available = (
            row["max_video_width_px"] is not None
            and row["max_video_height_px"] is not None
            and row["max_video_fps"] is not None
        )
        return {
            "id": row["id"],
            "catalog_id": f"catalog-camera-body-{row['id']}",
            "brand": row["brand"],
            "model": row["model"],
            "display_name": f"{row['brand']} {row['model']}",
            "body_type": body_type,
            "body_type_label": CAMERA_BODY_TYPE_LABELS.get(body_type, body_type),
            "sensor_format": sensor_format,
            "sensor_format_label": CAMERA_SENSOR_FORMAT_LABELS.get(
                sensor_format,
                sensor_format,
            ),
            "lens_mount": row["lens_mount"],
            "sensor_width_mm": row["sensor_width_mm"],
            "sensor_height_mm": row["sensor_height_mm"],
            "sensor_size_label": tr(
                "{width} × {height} mm",
                width=format_compact_number(row["sensor_width_mm"]),
                height=format_compact_number(row["sensor_height_mm"]),
            ),
            "resolution_width_px": row["resolution_width_px"],
            "resolution_height_px": row["resolution_height_px"],
            "resolution_label": tr(
                "{width} × {height} px",
                width=format_number(row["resolution_width_px"]),
                height=format_number(row["resolution_height_px"]),
            ),
            "pixel_size_um": pixel_size_um,
            "pixel_size_label": tr(
                "{value} µm",
                value=format_compact_number(pixel_size_um),
            ),
            "raw_bit_depth": row["raw_bit_depth"],
            "raw_bit_depth_label": tr(
                "RAW {value} bit",
                value=format_number(row["raw_bit_depth"]),
            ),
            "max_video_width_px": row["max_video_width_px"],
            "max_video_height_px": row["max_video_height_px"],
            "max_video_fps": row["max_video_fps"],
            "max_video_label": (
                tr(
                    "{width} × {height} @ {fps} fps",
                    width=format_number(row["max_video_width_px"]),
                    height=format_number(row["max_video_height_px"]),
                    fps=format_compact_number(row["max_video_fps"]),
                )
                if video_available
                else ""
            ),
            "live_view": bool(row["live_view"]),
            "bulb_mode": bool(row["bulb_mode"]),
            "source_url": row["source_url"] or "",
            "is_builtin": bool(row["is_builtin"]),
            "seed_key": row["seed_key"] or "",
            "is_user_modified": bool(row["is_user_modified"]),
        }

    @staticmethod
    def _filter_model(row: sqlite3.Row) -> dict:
        filter_class = str(row["filter_class"] or "").strip().upper()
        return {
            "id": row["id"],
            "catalog_id": f"catalog-filter-{row['id']}",
            "brand": row["brand"],
            "model": row["model"],
            "display_name": f"{row['brand']} {row['model']}",
            "filter_class": filter_class,
            "filter_class_label": FILTER_CLASS_LABELS.get(filter_class, filter_class),
            "central_wavelength_nm": row["central_wavelength_nm"],
            "bandwidth_nm": row["bandwidth_nm"],
            "transmission_pct": row["transmission_pct"],
            "minimum_aperture_mm": row["minimum_aperture_mm"],
            "bandwidth_label": (
                tr(
                    "{value} nm",
                    value=format_compact_number(row["bandwidth_nm"]),
                )
                if row["bandwidth_nm"] is not None
                else ""
            ),
            "transmission_label": (
                tr(
                    "{value}%",
                    value=format_compact_number(row["transmission_pct"]),
                )
                if row["transmission_pct"] is not None
                else ""
            ),
            "notes": row["notes"] or "",
            "is_builtin": bool(row["is_builtin"]),
            "seed_key": row["seed_key"] or "",
            "is_user_modified": bool(row["is_user_modified"]),
        }

    @staticmethod
    def _reducer_model(row: sqlite3.Row) -> dict:
        optical_system = str(row["optical_system"] or "").strip().upper()
        return {
            "id": row["id"],
            "catalog_id": f"catalog-reducer-{row['id']}",
            "brand": row["brand"],
            "model": row["model"],
            "display_name": f"{row['brand']} {row['model']}",
            "reduction_factor": row["reduction_factor"],
            "reduction_factor_label": tr(
                "{value}x",
                value=format_compact_number(row["reduction_factor"]),
            ),
            "optical_system": optical_system,
            "optical_system_label": OPTICAL_SYSTEM_LABELS.get(
                optical_system,
                optical_system,
            ),
            "connection": row["connection"] or "",
            "backfocus_mm": row["backfocus_mm"],
            "backfocus_label": (
                tr(
                    "{value} mm",
                    value=format_compact_number(row["backfocus_mm"]),
                )
                if row["backfocus_mm"] is not None
                else ""
            ),
            "visual_compatible": bool(row["visual_compatible"]),
            "imaging_compatible": bool(row["imaging_compatible"]),
            "corrected_field": bool(row["corrected_field"]),
            "notes": row["notes"] or "",
            "is_builtin": bool(row["is_builtin"]),
            "seed_key": row["seed_key"] or "",
            "is_user_modified": bool(row["is_user_modified"]),
        }

    @staticmethod
    def _validated_eyepiece_values(
        brand: str,
        model: str,
        eyepiece_type: str,
        focal_length_mm: float,
        apparent_field_deg: float,
        min_focal_length_mm: float | None,
        max_focal_length_mm: float | None,
        afov_min: float | None,
        afov_max: float | None,
        zoom_click_positions_mm: str,
        notes: str,
    ) -> tuple[tuple, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        clean_type = eyepiece_type.strip()
        if not clean_brand or not clean_model:
            return (), tr("Marca e modello sono obbligatori.")
        if not clean_type:
            return (), tr("Tipo di oculare non valido.")
        if clean_type.casefold() == "zoom":
            clean_type = "Zoom"
        if not _all_finite(
            focal_length_mm,
            apparent_field_deg,
            min_focal_length_mm,
            max_focal_length_mm,
            afov_min,
            afov_max,
        ):
            return (), tr("Dati oculare non validi.")
        if apparent_field_deg <= 0 or apparent_field_deg > 180:
            return (), tr("Il campo apparente deve essere compreso tra 0° e 180°.")
        if clean_type != "Zoom":
            if focal_length_mm <= 0:
                return (), tr("La focale deve essere maggiore di zero.")
            min_focal_length_mm = None
            max_focal_length_mm = None
        elif (
            min_focal_length_mm is None
            or max_focal_length_mm is None
            or min_focal_length_mm <= 0
            or min_focal_length_mm >= max_focal_length_mm
        ):
            return (), tr("Per uno Zoom indica una focale minima inferiore alla massima.")
        else:
            focal_length_mm = max_focal_length_mm
        if (afov_min is None) != (afov_max is None):
            return (), tr("L'intervallo AFOV deve contenere due valori.")
        if afov_min is not None and (
            afov_min <= 0 or afov_max is None or afov_min > afov_max or afov_max > 180
        ):
            return (), tr("L'intervallo AFOV non è valido.")
        return (
            clean_brand,
            clean_model,
            clean_type,
            focal_length_mm,
            min_focal_length_mm,
            max_focal_length_mm,
            apparent_field_deg,
            afov_min,
            afov_max,
            zoom_click_positions_mm.strip(),
            notes.strip(),
        ), ""

    @staticmethod
    def _validated_astronomy_camera_values(
        brand: str,
        model: str,
        camera_class: str,
        sensor_model: str,
        sensor_technology: str,
        color_mode: str,
        sensor_width_mm: float,
        sensor_height_mm: float,
        resolution_width_px: int,
        resolution_height_px: int,
        pixel_size_um: float,
        bit_depth: int,
        max_fps: float | None,
        cooled: bool,
        cooling_delta_c: float | None,
        shutter_type: str,
        backfocus_mm: float | None,
        source_url: str,
    ) -> tuple[tuple, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        clean_camera_class = camera_class.strip().upper()
        clean_sensor_model = sensor_model.strip()
        clean_sensor_technology = sensor_technology.strip().upper()
        clean_color_mode = color_mode.strip().upper()
        clean_shutter_type = shutter_type.strip().upper()
        clean_source_url = source_url.strip()
        if not clean_brand or not clean_model:
            return (), tr("Marca e modello sono obbligatori.")
        if not clean_sensor_model:
            return (), tr("Il modello del sensore è obbligatorio.")
        if clean_camera_class not in ASTRONOMY_CAMERA_CLASS_LABELS:
            return (), tr("Impiego della camera non valido.")
        if clean_sensor_technology not in SENSOR_TECHNOLOGY_LABELS:
            return (), tr("Tecnologia del sensore non valida.")
        if clean_color_mode not in SENSOR_COLOR_MODE_LABELS:
            return (), tr("Modalità colore del sensore non valida.")
        if clean_shutter_type not in SENSOR_SHUTTER_LABELS:
            return (), tr("Tipo di otturatore non valido.")
        if not _all_finite(
            sensor_width_mm,
            sensor_height_mm,
            pixel_size_um,
            max_fps,
            cooling_delta_c,
            backfocus_mm,
        ):
            return (), tr("Dati della camera astronomica non validi.")
        if sensor_width_mm <= 0 or sensor_height_mm <= 0 or pixel_size_um <= 0:
            return (), tr(
                "Le dimensioni del sensore e il passo pixel devono essere "
                "maggiori di zero."
            )
        if resolution_width_px <= 0 or resolution_height_px <= 0:
            return (), tr("La risoluzione deve essere maggiore di zero.")
        if bit_depth <= 0 or bit_depth > 32:
            return (), tr("La profondità in bit non è valida.")
        if max_fps is not None and max_fps <= 0:
            return (), tr("Il frame rate deve essere maggiore di zero.")
        if cooling_delta_c is not None and cooling_delta_c <= 0:
            return (), tr(
                "Il ΔT massimo sotto ambiente deve essere maggiore di zero."
            )
        if not cooled:
            cooling_delta_c = None
        if backfocus_mm is not None and backfocus_mm <= 0:
            return (), tr("Il backfocus deve essere maggiore di zero.")
        if clean_source_url and not clean_source_url.startswith(("https://", "http://")):
            return (), tr("Il collegamento alla fonte non è valido.")
        return (
            clean_brand,
            clean_model,
            clean_camera_class,
            clean_sensor_model,
            clean_sensor_technology,
            clean_color_mode,
            sensor_width_mm,
            sensor_height_mm,
            resolution_width_px,
            resolution_height_px,
            pixel_size_um,
            bit_depth,
            max_fps,
            1 if cooled else 0,
            cooling_delta_c,
            clean_shutter_type,
            backfocus_mm,
            clean_source_url,
        ), ""

    @staticmethod
    def _validated_camera_body_values(
        brand: str,
        model: str,
        body_type: str,
        sensor_format: str,
        lens_mount: str,
        sensor_width_mm: float,
        sensor_height_mm: float,
        resolution_width_px: int,
        resolution_height_px: int,
        raw_bit_depth: int,
        max_video_width_px: int | None,
        max_video_height_px: int | None,
        max_video_fps: float | None,
        live_view: bool,
        bulb_mode: bool,
        source_url: str,
    ) -> tuple[tuple, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        clean_body_type = body_type.strip().upper()
        clean_sensor_format = sensor_format.strip().upper()
        clean_lens_mount = lens_mount.strip()
        clean_source_url = source_url.strip()
        if not clean_brand or not clean_model:
            return (), tr("Marca e modello sono obbligatori.")
        if clean_body_type not in CAMERA_BODY_TYPE_LABELS:
            return (), tr("Tipo di corpo macchina non valido.")
        if clean_sensor_format not in CAMERA_SENSOR_FORMAT_LABELS:
            return (), tr("Formato del sensore non valido.")
        if not clean_lens_mount:
            return (), tr("La baionetta dell'obiettivo è obbligatoria.")
        if not _all_finite(sensor_width_mm, sensor_height_mm, max_video_fps):
            return (), tr("Dati del corpo macchina non validi.")
        if sensor_width_mm <= 0 or sensor_height_mm <= 0:
            return (), tr("Le dimensioni del sensore devono essere maggiori di zero.")
        if resolution_width_px <= 0 or resolution_height_px <= 0:
            return (), tr("La risoluzione deve essere maggiore di zero.")
        if raw_bit_depth <= 0 or raw_bit_depth > 32:
            return (), tr("La profondità RAW non è valida.")
        video_values = (
            max_video_width_px,
            max_video_height_px,
            max_video_fps,
        )
        if any(value is not None for value in video_values) and not all(
            value is not None for value in video_values
        ):
            return (), tr("Compila tutti i campi video oppure lasciali vuoti.")
        if all(value is not None for value in video_values) and (
            max_video_width_px is None
            or max_video_height_px is None
            or max_video_fps is None
            or max_video_width_px <= 0
            or max_video_height_px <= 0
            or max_video_fps <= 0
        ):
            return (), tr("I valori video devono essere maggiori di zero.")
        if clean_source_url and not clean_source_url.startswith(("https://", "http://")):
            return (), tr("Il collegamento alla fonte non è valido.")
        return (
            clean_brand,
            clean_model,
            clean_body_type,
            clean_sensor_format,
            clean_lens_mount,
            sensor_width_mm,
            sensor_height_mm,
            resolution_width_px,
            resolution_height_px,
            raw_bit_depth,
            max_video_width_px,
            max_video_height_px,
            max_video_fps,
            1 if live_view else 0,
            1 if bulb_mode else 0,
            clean_source_url,
        ), ""

    @staticmethod
    def _validated_filter_values(
        brand: str,
        model: str,
        filter_class: str,
        central_wavelength_nm: float | None,
        bandwidth_nm: float | None,
        transmission_pct: float | None,
        minimum_aperture_mm: int | None,
        notes: str,
    ) -> tuple[tuple, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        clean_class = filter_class.strip().upper()
        if not clean_brand or not clean_model:
            return (), tr("Marca e modello sono obbligatori.")
        if clean_class not in FILTER_CLASS_LABELS:
            return (), tr("Tipo di filtro non valido.")
        if central_wavelength_nm is not None and (
            not math.isfinite(central_wavelength_nm) or central_wavelength_nm <= 0
        ):
            return (), tr("La lunghezza d'onda deve essere maggiore di zero.")
        if bandwidth_nm is not None and (
            not math.isfinite(bandwidth_nm) or bandwidth_nm <= 0
        ):
            return (), tr("La larghezza di banda deve essere maggiore di zero.")
        if transmission_pct is not None and (
            not math.isfinite(transmission_pct) or not 0 < transmission_pct <= 100
        ):
            return (), tr("La trasmissione deve essere compresa tra 0 e 100%.")
        if minimum_aperture_mm is not None and minimum_aperture_mm <= 0:
            return (), tr("L'apertura minima deve essere maggiore di zero.")
        return (
            clean_brand,
            clean_model,
            clean_class,
            central_wavelength_nm,
            bandwidth_nm,
            transmission_pct,
            minimum_aperture_mm,
            notes.strip(),
        ), ""

    @staticmethod
    def _validated_reducer_values(
        brand: str,
        model: str,
        reduction_factor: float,
        optical_system: str,
        connection_name: str,
        backfocus_mm: float | None,
        visual_compatible: bool,
        imaging_compatible: bool,
        corrected_field: bool,
        notes: str,
    ) -> tuple[tuple, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        clean_system = optical_system.strip().upper()
        if not clean_brand or not clean_model:
            return (), tr("Marca e modello sono obbligatori.")
        if not math.isfinite(reduction_factor) or not 0 < reduction_factor < 1:
            return (), tr("Il fattore di riduzione deve essere compreso tra 0 e 1.")
        if clean_system not in OPTICAL_SYSTEM_LABELS:
            return (), tr("Sistema ottico non valido.")
        if backfocus_mm is not None and (
            not math.isfinite(backfocus_mm) or backfocus_mm <= 0
        ):
            return (), tr("Il backfocus deve essere maggiore di zero.")
        if not visual_compatible and not imaging_compatible:
            return (), tr("Indica almeno un impiego compatibile.")
        return (
            clean_brand,
            clean_model,
            reduction_factor,
            clean_system,
            connection_name.strip(),
            backfocus_mm,
            1 if visual_compatible else 0,
            1 if imaging_compatible else 0,
            1 if corrected_field else 0,
            notes.strip(),
        ), ""

    @staticmethod
    def _validated_reducer_telescope_ids(
        connection: sqlite3.Connection,
        compatible_telescope_ids: Iterable[str],
    ) -> tuple[tuple[int, ...], str]:
        model_ids: list[int] = []
        for value in compatible_telescope_ids:
            catalog_id = str(value or "").strip()
            prefix = "catalog-telescope-"
            if not catalog_id.startswith(prefix):
                return (), tr("Selezione dei telescopi compatibili non valida.")
            raw_model_id = catalog_id.removeprefix(prefix)
            if not raw_model_id.isdigit() or int(raw_model_id) <= 0:
                return (), tr("Selezione dei telescopi compatibili non valida.")
            model_id = int(raw_model_id)
            if model_id not in model_ids:
                model_ids.append(model_id)
        if not model_ids:
            return (), ""
        placeholders = ", ".join("?" for _ in model_ids)
        existing_ids = {
            int(row[0])
            for row in connection.execute(
                f"SELECT id FROM TelescopeModel WHERE id IN ({placeholders})",
                model_ids,
            ).fetchall()
        }
        if existing_ids != set(model_ids):
            return (), tr("Uno o più telescopi compatibili non esistono più.")
        return tuple(model_ids), ""

    @staticmethod
    def _replace_reducer_telescope_compatibility(
        connection: sqlite3.Connection,
        reducer_id: int,
        telescope_model_ids: Iterable[int],
    ) -> None:
        connection.execute(
            "DELETE FROM ReducerTelescopeCompatibility WHERE reducer_id = ?",
            (reducer_id,),
        )
        connection.executemany(
            """
            INSERT INTO ReducerTelescopeCompatibility (
                reducer_id, telescope_model_id
            )
            VALUES (?, ?)
            """,
            ((reducer_id, model_id) for model_id in telescope_model_ids),
        )

    @staticmethod
    def _ensure_brand(connection: sqlite3.Connection, brand: str) -> int:
        connection.execute("INSERT OR IGNORE INTO TelescopeBrand (name) VALUES (?)", (brand,))
        row = connection.execute("SELECT id FROM TelescopeBrand WHERE name = ?", (brand,)).fetchone()
        return int(row["id"])

    @staticmethod
    def _validated_smart_capabilities(
        instrument_category: str,
        capabilities: Mapping[str, object] | None,
    ) -> tuple[dict[str, object], str]:
        if instrument_category != "SMART_INTEGRATED":
            return {}, ""
        values = capabilities or {}

        def optional_float(key: str) -> float | None:
            raw_value = values.get(key)
            if raw_value in (None, ""):
                return None
            if isinstance(raw_value, bool):
                raise ValueError
            number = float(str(raw_value).strip().replace(",", "."))
            if not math.isfinite(number) or number <= 0:
                raise ValueError
            return number

        def optional_int(key: str) -> int | None:
            number = optional_float(key)
            if number is None:
                return None
            integer = int(number)
            if number != integer:
                raise ValueError
            return integer

        def boolean(key: str) -> bool:
            raw_value = values.get(key, False)
            if isinstance(raw_value, str):
                normalized = raw_value.strip().casefold()
                if normalized in {
                    "1",
                    "true",
                    "yes",
                    "on",
                    "si",
                    "sì",
                }:
                    return True
                if normalized in {"", "0", "false", "no", "off"}:
                    return False
                raise ValueError
            return bool(raw_value)

        try:
            color_mode = str(values.get("color_mode") or "").strip().upper()
            if color_mode and color_mode not in SENSOR_COLOR_MODE_LABELS:
                raise ValueError
            exposure_control_mode = str(
                values.get("exposure_control_mode") or "DEVICE_MANAGED"
            ).strip().upper()
            if exposure_control_mode not in {
                "DEVICE_MANAGED",
                "USER_CONFIGURABLE",
            }:
                raise ValueError
            raw_filter_codes = values.get("integrated_filter_codes") or ""
            if isinstance(raw_filter_codes, str):
                filter_tokens = re.split(r"[,;/]+", raw_filter_codes)
            elif isinstance(raw_filter_codes, Iterable):
                filter_tokens = [str(value) for value in raw_filter_codes]
            else:
                raise ValueError
            filter_codes = tuple(
                dict.fromkeys(
                    token.strip().upper().replace(" ", "_")
                    for token in filter_tokens
                    if token.strip()
                )
            )
            if any(
                not re.fullmatch(r"[A-Z0-9_+-]+", code)
                for code in filter_codes
            ):
                raise ValueError
            parsed = {
                "supports_optical_visual": boolean(
                    "supports_optical_visual"
                ),
                "supports_interchangeable_eyepieces": boolean(
                    "supports_interchangeable_eyepieces"
                ),
                "supports_external_cameras": boolean(
                    "supports_external_cameras"
                ),
                "supports_external_optical_modifiers": boolean(
                    "supports_external_optical_modifiers"
                ),
                "sensor_model": str(
                    values.get("sensor_model") or ""
                ).strip(),
                "sensor_width_mm": optional_float("sensor_width_mm"),
                "sensor_height_mm": optional_float("sensor_height_mm"),
                "resolution_width_px": optional_int(
                    "resolution_width_px"
                ),
                "resolution_height_px": optional_int(
                    "resolution_height_px"
                ),
                "pixel_size_um": optional_float("pixel_size_um"),
                "bit_depth": optional_int("bit_depth"),
                "color_mode": color_mode,
                "full_resolution_fps": optional_float(
                    "full_resolution_fps"
                ),
                "supports_live_stacking": boolean(
                    "supports_live_stacking"
                ),
                "supports_video": boolean("supports_video"),
                "supports_mosaic": boolean("supports_mosaic"),
                "exposure_control_mode": exposure_control_mode,
                "integrated_filter_codes": ";".join(filter_codes),
                "specification_source_url": str(
                    values.get("specification_source_url") or ""
                ).strip(),
            }
            if not parsed["supports_optical_visual"]:
                parsed["supports_interchangeable_eyepieces"] = False
        except (TypeError, ValueError):
            return {}, tr(
                "Le specifiche integrate del telescopio smart non sono valide."
            )
        return parsed, ""

    @staticmethod
    def _replace_smart_capabilities(
        connection: sqlite3.Connection,
        model_id: int,
        values: Mapping[str, object],
    ) -> None:
        connection.execute(
            """
            INSERT INTO SmartTelescopeCapability (
                telescope_model_id, supports_optical_visual,
                supports_interchangeable_eyepieces,
                supports_external_cameras,
                supports_external_optical_modifiers, sensor_model,
                sensor_width_mm, sensor_height_mm, resolution_width_px,
                resolution_height_px, pixel_size_um, bit_depth, color_mode,
                full_resolution_fps, supports_live_stacking, supports_video,
                supports_mosaic, exposure_control_mode,
                integrated_filter_codes, specification_source_url
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(telescope_model_id) DO UPDATE SET
                supports_optical_visual =
                    excluded.supports_optical_visual,
                supports_interchangeable_eyepieces =
                    excluded.supports_interchangeable_eyepieces,
                supports_external_cameras =
                    excluded.supports_external_cameras,
                supports_external_optical_modifiers =
                    excluded.supports_external_optical_modifiers,
                sensor_model = excluded.sensor_model,
                sensor_width_mm = excluded.sensor_width_mm,
                sensor_height_mm = excluded.sensor_height_mm,
                resolution_width_px = excluded.resolution_width_px,
                resolution_height_px = excluded.resolution_height_px,
                pixel_size_um = excluded.pixel_size_um,
                bit_depth = excluded.bit_depth,
                color_mode = excluded.color_mode,
                full_resolution_fps = excluded.full_resolution_fps,
                supports_live_stacking = excluded.supports_live_stacking,
                supports_video = excluded.supports_video,
                supports_mosaic = excluded.supports_mosaic,
                exposure_control_mode = excluded.exposure_control_mode,
                integrated_filter_codes =
                    excluded.integrated_filter_codes,
                specification_source_url =
                    excluded.specification_source_url
            """,
            (
                model_id,
                int(bool(values["supports_optical_visual"])),
                int(bool(values["supports_interchangeable_eyepieces"])),
                int(bool(values["supports_external_cameras"])),
                int(bool(values["supports_external_optical_modifiers"])),
                values["sensor_model"],
                values["sensor_width_mm"],
                values["sensor_height_mm"],
                values["resolution_width_px"],
                values["resolution_height_px"],
                values["pixel_size_um"],
                values["bit_depth"],
                values["color_mode"] or None,
                values["full_resolution_fps"],
                int(bool(values["supports_live_stacking"])),
                int(bool(values["supports_video"])),
                int(bool(values["supports_mosaic"])),
                values["exposure_control_mode"],
                values["integrated_filter_codes"],
                values["specification_source_url"],
            ),
        )

    def _telescope_model_by_id(self, connection: sqlite3.Connection, model_id: int) -> dict | None:
        row = connection.execute(
            f"""
            SELECT tm.id, tb.name AS brand, tm.name, tm.instrument_category,
                   tm.optical_type, tm.aperture_mm, tm.focal_length_mm,
                   tm.focal_ratio, tm.mount_type, tm.notes, tm.is_builtin,
                   tm.seed_key, tm.is_user_modified,
                   {_SMART_CAPABILITY_COLUMNS}
            FROM TelescopeModel tm
            JOIN TelescopeBrand tb ON tb.id = tm.brand_id
            LEFT JOIN SmartTelescopeCapability sc
              ON sc.telescope_model_id = tm.id
            WHERE tm.id = ?
            LIMIT 1
            """,
            (model_id,),
        ).fetchone()
        return self._telescope_model(row) if row else None

    @staticmethod
    def _is_builtin(
        connection: sqlite3.Connection,
        table_name: str,
        item_id: int,
    ) -> bool:
        row = connection.execute(
            f"SELECT is_builtin FROM {table_name} WHERE id = ?",
            (item_id,),
        ).fetchone()
        return bool(row and row["is_builtin"])
