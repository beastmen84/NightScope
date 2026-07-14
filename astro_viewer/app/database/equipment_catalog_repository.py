from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path

from astro_viewer.app.models.filtering import FILTER_CLASS_LABELS
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


class EquipmentCatalogRepository:
    """SQLite access for global equipment catalogs and profile assignments."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def brands(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT id, name FROM TelescopeBrand ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def models(self, brand_id: int | None = None) -> list[dict]:
        query = """
            SELECT tm.id, tb.name AS brand, tm.name, tm.optical_type,
                   tm.aperture_mm, tm.focal_length_mm, tm.focal_ratio,
                   tm.mount_type, tm.notes, tm.is_builtin, tm.seed_key,
                   tm.is_user_modified
            FROM TelescopeModel tm
            JOIN TelescopeBrand tb ON tb.id = tm.brand_id
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
                    """
                    SELECT tm.id, tb.name AS brand, tm.name, tm.optical_type,
                           tm.aperture_mm, tm.focal_length_mm, tm.focal_ratio,
                           tm.mount_type, tm.notes, tm.is_builtin, tm.seed_key,
                           tm.is_user_modified
                    FROM TelescopeModel tm
                    JOIN TelescopeBrand tb ON tb.id = tm.brand_id
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
                """
                SELECT tm.id, tb.name AS brand, tm.name, tm.optical_type,
                       tm.aperture_mm, tm.focal_length_mm, tm.focal_ratio,
                       tm.mount_type, tm.notes, tm.is_builtin, tm.seed_key,
                       tm.is_user_modified
                FROM TelescopeModel tm
                JOIN TelescopeBrand tb ON tb.id = tm.brand_id
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
    ) -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_name = name.strip()
        if not clean_brand or not clean_name:
            return False, tr("Marca e modello sono obbligatori.")
        clean_optical_type = optical_type.strip()
        clean_mount_type = mount_type.strip()
        if not clean_optical_type or not clean_mount_type:
            return False, tr("Tipo ottico e montatura sono obbligatori.")
        if aperture_mm <= 0 or focal_length_mm <= 0:
            return False, tr("Apertura e focale devono essere maggiori di zero.")
        with closing(self._connect()) as connection:
            brand_id = self._ensure_brand(connection, clean_brand)
            duplicate = connection.execute(
                "SELECT id FROM TelescopeModel WHERE brand_id = ? AND name = ?",
                (brand_id, clean_name),
            ).fetchone()
            if duplicate:
                return False, tr("Questo modello è già presente nel catalogo.")
            focal_ratio = round(focal_length_mm / aperture_mm, 1) if aperture_mm > 0 else None
            connection.execute(
                """
                INSERT INTO TelescopeModel (
                    brand_id, name, optical_type, aperture_mm, focal_length_mm,
                    focal_ratio, mount_type, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brand_id,
                    clean_name,
                    clean_optical_type,
                    aperture_mm,
                    focal_length_mm,
                    focal_ratio,
                    clean_mount_type,
                    notes.strip(),
                ),
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
    ) -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_name = name.strip()
        if not clean_brand or not clean_name:
            return False, tr("Marca e modello sono obbligatori.")
        clean_optical_type = optical_type.strip()
        clean_mount_type = mount_type.strip()
        if not clean_optical_type or not clean_mount_type:
            return False, tr("Tipo ottico e montatura sono obbligatori.")
        if aperture_mm <= 0 or focal_length_mm <= 0:
            return False, tr("Apertura e focale devono essere maggiori di zero.")
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
                SET brand_id = ?, name = ?, optical_type = ?, aperture_mm = ?,
                    focal_length_mm = ?, focal_ratio = ?, mount_type = ?, notes = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                (
                    brand_id,
                    clean_name,
                    clean_optical_type,
                    aperture_mm,
                    focal_length_mm,
                    focal_ratio,
                    clean_mount_type,
                    notes.strip(),
                    model_id,
                ),
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
            used = self._profile_usage_count(connection, "telescope", catalog_id, legacy_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                self._remove_from_profiles(connection, "telescope", catalog_id, legacy_id)
            connection.execute("DELETE FROM TelescopeModel WHERE id = ?", (model_id,))
            connection.commit()
        return True, tr("Modello telescopio eliminato.")

    def eyepieces(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, eyepiece_type, focal_length_mm,
                       min_focal_length_mm, max_focal_length_mm,
                       apparent_field_deg, afov_min, afov_max, barrel_size,
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
        barrel_size: str,
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
            barrel_size,
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
                    max_focal_length_mm, apparent_field_deg, afov_min, afov_max, barrel_size,
                    zoom_click_positions_mm, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        barrel_size: str,
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
            barrel_size,
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
            if not values[10]:
                values = values[:10] + (
                    existing["zoom_click_positions_mm"] or "",
                    values[11],
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
                    barrel_size = ?, zoom_click_positions_mm = ?, notes = ?,
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
            used = self._profile_usage_count(connection, "eyepiece", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                self._remove_from_profiles(connection, "eyepiece", catalog_id)
            connection.execute("DELETE FROM EyepieceCatalog WHERE id = ?", (eyepiece_id,))
            connection.commit()
        return True, tr("Oculare eliminato.")

    def barlows(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, multiplier, barrel_size, notes,
                       is_builtin, seed_key, is_user_modified
                FROM BarlowCatalog
                ORDER BY brand, model, multiplier
                """
            ).fetchall()
        return [self._barlow_model(row) for row in rows]

    def add_barlow(self, brand: str, model: str, multiplier: float, barrel_size: str, notes: str = "") -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, tr("Marca e modello sono obbligatori.")
        if multiplier <= 1:
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
                INSERT INTO BarlowCatalog (brand, model, multiplier, barrel_size, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (clean_brand, clean_model, multiplier, barrel_size.strip(), notes.strip()),
            )
            connection.commit()
        return True, tr("Barlow aggiunta.")

    def update_barlow(self, barlow_id: int, brand: str, model: str, multiplier: float, barrel_size: str, notes: str = "") -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, tr("Marca e modello sono obbligatori.")
        if multiplier <= 1:
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
                SET brand = ?, model = ?, multiplier = ?, barrel_size = ?, notes = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                (
                    clean_brand,
                    clean_model,
                    multiplier,
                    barrel_size.strip(),
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
            used = self._profile_usage_count(connection, "barlow", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                self._remove_from_profiles(connection, "barlow", catalog_id)
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
                ORDER BY brand, model, magnification, objective_diameter_mm
                """
            ).fetchall()
        return [self._binocular_model(row) for row in rows]

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
        if magnification <= 0 or objective_diameter_mm <= 0:
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
        if magnification <= 0 or objective_diameter_mm <= 0:
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
            used = self._profile_usage_count(connection, "binocular", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                self._remove_from_profiles(connection, "binocular", catalog_id)
            connection.execute("DELETE FROM BinocularCatalog WHERE id = ?", (binocular_id,))
            connection.commit()
        return True, tr("Binocolo eliminato.")

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
            used = self._profile_usage_count(connection, "filter", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                self._remove_from_profiles(connection, "filter", catalog_id)
            connection.execute("DELETE FROM FilterCatalog WHERE id = ?", (filter_id,))
            connection.commit()
        return True, tr("Filtro eliminato.")

    def reducers(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, reduction_factor, optical_system,
                       compatible_models, connection, backfocus_mm,
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
            if compatibility:
                reducer["compatible_models"] = "; ".join(
                    item["display_name"] for item in compatibility
                )
            reducers.append(reducer)
        return reducers

    def add_reducer(
        self,
        brand: str,
        model: str,
        reduction_factor: float,
        optical_system: str,
        compatible_models: str = "",
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
            compatible_models,
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
                    compatible_models, connection, backfocus_mm,
                    visual_compatible, imaging_compatible, corrected_field,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        compatible_models: str = "",
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
            compatible_models,
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
            existing = connection.execute(
                "SELECT id, is_builtin FROM ReducerCatalog WHERE id = ?",
                (reducer_id,),
            ).fetchone()
            if not existing:
                return False, tr("Riduttore non trovato.")
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
                    optical_system = ?, compatible_models = ?, connection = ?,
                    backfocus_mm = ?, visual_compatible = ?,
                    imaging_compatible = ?, corrected_field = ?, notes = ?,
                    is_user_modified = CASE
                        WHEN is_builtin = 1 THEN 1 ELSE is_user_modified
                    END
                WHERE id = ?
                """,
                values + (reducer_id,),
            )
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
            used = self._profile_usage_count(connection, "reducer", catalog_id)
            if used and not remove_from_profiles:
                return False, tr("Questo elemento è utilizzato da uno o più profili.")
            if remove_from_profiles:
                self._remove_from_profiles(connection, "reducer", catalog_id)
            connection.execute("DELETE FROM ReducerCatalog WHERE id = ?", (reducer_id,))
            connection.commit()
        return True, tr("Riduttore eliminato.")

    def profiles(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, profile_name, active, telescope_id
                FROM EquipmentProfile
                ORDER BY active DESC, profile_name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def set_active_profile(self, profile_id: int) -> None:
        with closing(self._connect()) as connection:
            connection.execute("UPDATE EquipmentProfile SET active = 0")
            connection.execute("UPDATE EquipmentProfile SET active = 1 WHERE id = ?", (profile_id,))
            connection.commit()

    def active_profile(self) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT id, profile_name, active, telescope_id
                FROM EquipmentProfile
                WHERE active = 1
                LIMIT 1
                """
            ).fetchone()
        return dict(row) if row else None

    def add_profile(self, profile_name: str, telescope_id: str, active: bool = False) -> None:
        with closing(self._connect()) as connection:
            if active:
                connection.execute("UPDATE EquipmentProfile SET active = 0")
            connection.execute(
                """
                INSERT INTO EquipmentProfile (profile_name, active, telescope_id)
                VALUES (?, ?, ?)
                ON CONFLICT(profile_name) DO UPDATE SET
                    active = excluded.active,
                    telescope_id = excluded.telescope_id
                """,
                (profile_name, 1 if active else 0, telescope_id),
            )
            profile = connection.execute(
                "SELECT id FROM EquipmentProfile WHERE profile_name = ?",
                (profile_name,),
            ).fetchone()
            if profile and telescope_id != "preset:naked-eye":
                connection.execute(
                    """
                    INSERT OR IGNORE INTO EquipmentProfileTelescope (profile_id, telescope_id)
                    VALUES (?, ?)
                    """,
                    (profile["id"], telescope_id),
                )
            connection.commit()

    def rename_profile(self, profile_id: int, profile_name: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute("UPDATE EquipmentProfile SET profile_name = ? WHERE id = ?", (profile_name, profile_id))
            connection.commit()

    def update_profile_telescope(self, profile_id: int, telescope_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute("UPDATE EquipmentProfile SET telescope_id = ? WHERE id = ?", (telescope_id, profile_id))
            connection.commit()

    def delete_profile(self, profile_id: int) -> None:
        with closing(self._connect()) as connection:
            active = connection.execute("SELECT active FROM EquipmentProfile WHERE id = ?", (profile_id,)).fetchone()
            connection.execute("DELETE FROM EquipmentProfile WHERE id = ?", (profile_id,))
            if active and int(active["active"]) == 1:
                replacement = connection.execute("SELECT id FROM EquipmentProfile ORDER BY profile_name LIMIT 1").fetchone()
                if replacement:
                    connection.execute("UPDATE EquipmentProfile SET active = 1 WHERE id = ?", (replacement["id"],))
                else:
                    connection.execute(
                        """
                        INSERT INTO EquipmentProfile (profile_name, active, telescope_id)
                        VALUES (?, 1, ?)
                        """,
                        ("Default", "preset:naked-eye"),
                    )
            connection.commit()

    def profile_telescope_ids(self, profile_id: int) -> list[str]:
        return self._profile_item_ids("EquipmentProfileTelescope", "telescope_id", profile_id)

    def profile_eyepiece_ids(self, profile_id: int) -> list[str]:
        return self._profile_item_ids("EquipmentProfileEyepiece", "eyepiece_id", profile_id)

    def profile_barlow_ids(self, profile_id: int) -> list[str]:
        return self._profile_item_ids("EquipmentProfileBarlow", "barlow_id", profile_id)

    def profile_binocular_ids(self, profile_id: int) -> list[str]:
        return self._profile_item_ids("EquipmentProfileBinocular", "binocular_id", profile_id)

    def profile_filter_ids(self, profile_id: int) -> list[str]:
        return self._profile_item_ids("EquipmentProfileFilter", "filter_id", profile_id)

    def profile_reducer_ids(self, profile_id: int) -> list[str]:
        return self._profile_item_ids("EquipmentProfileReducer", "reducer_id", profile_id)

    def assign_profile_telescope(self, profile_id: int, telescope_id: str) -> None:
        self._assign_profile_item("EquipmentProfileTelescope", "telescope_id", profile_id, telescope_id)

    def remove_profile_telescope(self, profile_id: int, telescope_id: str) -> None:
        self._remove_profile_item("EquipmentProfileTelescope", "telescope_id", profile_id, telescope_id)

    def assign_profile_eyepiece(self, profile_id: int, eyepiece_id: str) -> None:
        self._assign_profile_item("EquipmentProfileEyepiece", "eyepiece_id", profile_id, eyepiece_id)

    def remove_profile_eyepiece(self, profile_id: int, eyepiece_id: str) -> None:
        self._remove_profile_item("EquipmentProfileEyepiece", "eyepiece_id", profile_id, eyepiece_id)

    def assign_profile_barlow(self, profile_id: int, barlow_id: str) -> None:
        self._assign_profile_item("EquipmentProfileBarlow", "barlow_id", profile_id, barlow_id)

    def remove_profile_barlow(self, profile_id: int, barlow_id: str) -> None:
        self._remove_profile_item("EquipmentProfileBarlow", "barlow_id", profile_id, barlow_id)

    def assign_profile_binocular(self, profile_id: int, binocular_id: str) -> None:
        self._assign_profile_item("EquipmentProfileBinocular", "binocular_id", profile_id, binocular_id)

    def remove_profile_binocular(self, profile_id: int, binocular_id: str) -> None:
        self._remove_profile_item("EquipmentProfileBinocular", "binocular_id", profile_id, binocular_id)

    def assign_profile_filter(self, profile_id: int, filter_id: str) -> None:
        self._assign_profile_item("EquipmentProfileFilter", "filter_id", profile_id, filter_id)

    def remove_profile_filter(self, profile_id: int, filter_id: str) -> None:
        self._remove_profile_item("EquipmentProfileFilter", "filter_id", profile_id, filter_id)

    def assign_profile_reducer(self, profile_id: int, reducer_id: str) -> None:
        self._assign_profile_item("EquipmentProfileReducer", "reducer_id", profile_id, reducer_id)

    def remove_profile_reducer(self, profile_id: int, reducer_id: str) -> None:
        self._remove_profile_item("EquipmentProfileReducer", "reducer_id", profile_id, reducer_id)

    def profile_usage_count(self, kind: str, item_id: str) -> int:
        with closing(self._connect()) as connection:
            return self._profile_usage_count(connection, kind, item_id)

    def _profile_item_ids(self, table: str, id_column: str, profile_id: int) -> list[str]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"SELECT {id_column} FROM {table} WHERE profile_id = ? ORDER BY {id_column}",
                (profile_id,),
            ).fetchall()
        return [row[id_column] for row in rows]

    def _assign_profile_item(self, table: str, id_column: str, profile_id: int, item_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(f"INSERT OR IGNORE INTO {table} (profile_id, {id_column}) VALUES (?, ?)", (profile_id, item_id))
            connection.commit()

    def _remove_profile_item(self, table: str, id_column: str, profile_id: int, item_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(f"DELETE FROM {table} WHERE profile_id = ? AND {id_column} = ?", (profile_id, item_id))
            connection.commit()

    @staticmethod
    def _telescope_model(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "brand": row["brand"],
            "name": row["name"],
            "display_name": f"{row['brand']} {row['name']}",
            "optical_type": row["optical_type"],
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
            "mount_type": row["mount_type"],
            "notes": row["notes"] or "",
            "is_builtin": bool(row["is_builtin"]),
            "seed_key": row["seed_key"] or "",
            "is_user_modified": bool(row["is_user_modified"]),
            "catalog_id": f"catalog-telescope-{row['id']}",
            "legacy_catalog_id": f"catalog:{row['brand']}:{row['name']}",
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
                "{value} gradi",
                value=format_compact_number(row["apparent_field_deg"]),
            ),
            "afov_min": row["afov_min"],
            "afov_max": row["afov_max"],
            "barrel_size": row["barrel_size"] or "",
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
            "barrel_size": row["barrel_size"] or "",
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
            "compatible_models": row["compatible_models"] or "",
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
        barrel_size: str,
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
        if apparent_field_deg <= 0 or apparent_field_deg > 180:
            return (), tr("Il campo apparente deve essere compreso tra 0 e 180 gradi.")
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
            barrel_size.strip(),
            zoom_click_positions_mm.strip(),
            notes.strip(),
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
        if central_wavelength_nm is not None and central_wavelength_nm <= 0:
            return (), tr("La lunghezza d'onda deve essere maggiore di zero.")
        if bandwidth_nm is not None and bandwidth_nm <= 0:
            return (), tr("La larghezza di banda deve essere maggiore di zero.")
        if transmission_pct is not None and not 0 < transmission_pct <= 100:
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
        compatible_models: str,
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
        if not 0 < reduction_factor < 1:
            return (), tr("Il fattore di riduzione deve essere compreso tra 0 e 1.")
        if clean_system not in OPTICAL_SYSTEM_LABELS:
            return (), tr("Sistema ottico non valido.")
        if backfocus_mm is not None and backfocus_mm <= 0:
            return (), tr("Il backfocus deve essere maggiore di zero.")
        if not visual_compatible and not imaging_compatible:
            return (), tr("Indica almeno un impiego compatibile.")
        return (
            clean_brand,
            clean_model,
            reduction_factor,
            clean_system,
            compatible_models.strip(),
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

    def _telescope_model_by_id(self, connection: sqlite3.Connection, model_id: int) -> dict | None:
        row = connection.execute(
            """
            SELECT tm.id, tb.name AS brand, tm.name, tm.optical_type,
                   tm.aperture_mm, tm.focal_length_mm, tm.focal_ratio,
                   tm.mount_type, tm.notes, tm.is_builtin, tm.seed_key,
                   tm.is_user_modified
            FROM TelescopeModel tm
            JOIN TelescopeBrand tb ON tb.id = tm.brand_id
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

    def _profile_usage_count(self, connection: sqlite3.Connection, kind: str, item_id: str, legacy_id: str | None = None) -> int:
        ids = [item_id]
        if legacy_id and legacy_id != item_id:
            ids.append(legacy_id)
        placeholders = ", ".join("?" for _ in ids)
        if kind == "telescope":
            query = f"""
                SELECT COUNT(*)
                FROM (
                    SELECT assignment.profile_id
                    FROM EquipmentProfileTelescope assignment
                    JOIN EquipmentProfile profile ON profile.id = assignment.profile_id
                    WHERE assignment.telescope_id IN ({placeholders})
                    UNION
                    SELECT profile.id
                    FROM EquipmentProfile profile
                    WHERE profile.telescope_id IN ({placeholders})
                )
            """
            return int(connection.execute(query, [*ids, *ids]).fetchone()[0])
        assignment_tables = {
            "eyepiece": ("EquipmentProfileEyepiece", "eyepiece_id"),
            "barlow": ("EquipmentProfileBarlow", "barlow_id"),
            "binocular": ("EquipmentProfileBinocular", "binocular_id"),
            "filter": ("EquipmentProfileFilter", "filter_id"),
            "reducer": ("EquipmentProfileReducer", "reducer_id"),
        }
        assignment = assignment_tables.get(kind)
        if assignment is None:
            return 0
        table_name, id_column = assignment
        return int(
            connection.execute(
                f"""
                SELECT COUNT(DISTINCT assignment.profile_id)
                FROM {table_name} assignment
                JOIN EquipmentProfile profile ON profile.id = assignment.profile_id
                WHERE assignment.{id_column} IN ({placeholders})
                """,
                ids,
            ).fetchone()[0]
        )

    @staticmethod
    def _remove_from_profiles(connection: sqlite3.Connection, kind: str, item_id: str, legacy_id: str | None = None) -> None:
        ids = [item_id]
        if legacy_id and legacy_id != item_id:
            ids.append(legacy_id)
        placeholders = ", ".join("?" for _ in ids)
        if kind == "telescope":
            connection.execute(f"DELETE FROM EquipmentProfileTelescope WHERE telescope_id IN ({placeholders})", ids)
            connection.execute(
                f"UPDATE EquipmentProfile SET telescope_id = ? WHERE telescope_id IN ({placeholders})",
                ["preset:naked-eye", *ids],
            )
        elif kind == "eyepiece":
            connection.execute(f"DELETE FROM EquipmentProfileEyepiece WHERE eyepiece_id IN ({placeholders})", ids)
        elif kind == "barlow":
            connection.execute(f"DELETE FROM EquipmentProfileBarlow WHERE barlow_id IN ({placeholders})", ids)
        elif kind == "binocular":
            connection.execute(f"DELETE FROM EquipmentProfileBinocular WHERE binocular_id IN ({placeholders})", ids)
        elif kind == "filter":
            connection.execute(f"DELETE FROM EquipmentProfileFilter WHERE filter_id IN ({placeholders})", ids)
        elif kind == "reducer":
            connection.execute(f"DELETE FROM EquipmentProfileReducer WHERE reducer_id IN ({placeholders})", ids)
