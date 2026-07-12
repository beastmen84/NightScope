from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


FILTER_CLASS_LABELS = {
    "UHC": "UHC",
    "OIII": "OIII",
    "H_BETA": "H-beta",
    "CLS": "Riduzione inquinamento luminoso",
    "MOON_SKYGLOW": "Luna e contrasto",
    "ND": "Densità neutra",
    "POLARIZING": "Polarizzatore",
    "COLOR": "Colorato planetario",
    "CONTRAST": "Contrasto planetario",
    "CHROMATIC": "Correzione cromatica",
    "COMET": "Comete",
}

OPTICAL_SYSTEM_LABELS = {
    "SCT_CLASSIC": "SCT classico",
    "EDGEHD": "EdgeHD",
    "REFRACTOR": "Rifrattore",
    "RC": "Ritchey-Chrétien",
    "UNIVERSAL": "Universale",
    "OTHER": "Altro",
}


class EquipmentCatalogRepository:
    """SQLite access for global equipment catalogs and profile assignments."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
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
                   tm.mount_type, tm.notes, tm.is_builtin
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
                           tm.mount_type, tm.notes, tm.is_builtin
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
                       tm.mount_type, tm.notes, tm.is_builtin
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
            return False, "Marca e modello sono obbligatori."
        with closing(self._connect()) as connection:
            brand_id = self._ensure_brand(connection, clean_brand)
            duplicate = connection.execute(
                "SELECT id FROM TelescopeModel WHERE brand_id = ? AND name = ?",
                (brand_id, clean_name),
            ).fetchone()
            if duplicate:
                return False, "Questo modello è già presente nel catalogo."
            focal_ratio = round(focal_length_mm / aperture_mm, 1) if aperture_mm > 0 else None
            connection.execute(
                """
                INSERT INTO TelescopeModel (
                    brand_id, name, optical_type, aperture_mm, focal_length_mm,
                    focal_ratio, mount_type, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (brand_id, clean_name, optical_type, aperture_mm, focal_length_mm, focal_ratio, mount_type, notes),
            )
            connection.commit()
        return True, "Modello telescopio aggiunto."

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
            return False, "Marca e modello sono obbligatori."
        with closing(self._connect()) as connection:
            old = self._telescope_model_by_id(connection, model_id)
            if not old:
                return False, "Modello telescopio non trovato."
            brand_id = self._ensure_brand(connection, clean_brand)
            duplicate = connection.execute(
                "SELECT id FROM TelescopeModel WHERE brand_id = ? AND name = ? AND id <> ?",
                (brand_id, clean_name, model_id),
            ).fetchone()
            if duplicate:
                return False, "Questo modello è già presente nel catalogo."
            focal_ratio = round(focal_length_mm / aperture_mm, 1) if aperture_mm > 0 else None
            connection.execute(
                """
                UPDATE TelescopeModel
                SET brand_id = ?, name = ?, optical_type = ?, aperture_mm = ?,
                    focal_length_mm = ?, focal_ratio = ?, mount_type = ?, notes = ?
                WHERE id = ?
                """,
                (brand_id, clean_name, optical_type, aperture_mm, focal_length_mm, focal_ratio, mount_type, notes, model_id),
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
        return True, "Modello telescopio aggiornato."

    def delete_telescope_model(self, model_id: int, remove_from_profiles: bool = False) -> tuple[bool, str]:
        catalog_id = f"catalog-telescope-{model_id}"
        legacy_id = None
        with closing(self._connect()) as connection:
            old = self._telescope_model_by_id(connection, model_id)
            if not old:
                return False, "Modello telescopio non trovato."
            if old["is_builtin"]:
                return False, "Gli elementi integrati non possono essere eliminati."
            legacy_id = old.get("legacy_catalog_id")
            used = self._profile_usage_count(connection, "telescope", catalog_id, legacy_id)
            if used and not remove_from_profiles:
                return False, "Questo elemento è utilizzato da uno o più profili."
            if remove_from_profiles:
                self._remove_from_profiles(connection, "telescope", catalog_id, legacy_id)
            connection.execute("DELETE FROM TelescopeModel WHERE id = ?", (model_id,))
            connection.commit()
        return True, "Modello telescopio eliminato."

    def eyepieces(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, eyepiece_type, focal_length_mm,
                       min_focal_length_mm, max_focal_length_mm,
                       apparent_field_deg, afov_min, afov_max, barrel_size,
                       zoom_click_positions_mm, notes, is_builtin
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
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, "Marca e modello sono obbligatori."
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                """
                SELECT id FROM EyepieceCatalog
                WHERE brand = ? AND model = ? AND focal_length_mm = ?
                """,
                (clean_brand, clean_model, focal_length_mm),
            ).fetchone()
            if duplicate:
                return False, "Questo oculare è già presente nel catalogo."
            connection.execute(
                """
                INSERT INTO EyepieceCatalog (
                    brand, model, eyepiece_type, focal_length_mm, min_focal_length_mm,
                    max_focal_length_mm, apparent_field_deg, afov_min, afov_max, barrel_size,
                    zoom_click_positions_mm, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_brand,
                    clean_model,
                    eyepiece_type,
                    focal_length_mm,
                    min_focal_length_mm,
                    max_focal_length_mm,
                    apparent_field_deg,
                    afov_min,
                    afov_max,
                    barrel_size,
                    zoom_click_positions_mm,
                    notes,
                ),
            )
            connection.commit()
        return True, "Oculare aggiunto."

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
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, "Marca e modello sono obbligatori."
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                """
                SELECT id FROM EyepieceCatalog
                WHERE brand = ? AND model = ? AND focal_length_mm = ? AND id <> ?
                """,
                (clean_brand, clean_model, focal_length_mm, eyepiece_id),
            ).fetchone()
            if duplicate:
                return False, "Questo oculare è già presente nel catalogo."
            connection.execute(
                """
                UPDATE EyepieceCatalog
                SET brand = ?, model = ?, eyepiece_type = ?, focal_length_mm = ?,
                    min_focal_length_mm = ?, max_focal_length_mm = ?,
                    apparent_field_deg = ?, afov_min = ?, afov_max = ?,
                    barrel_size = ?, zoom_click_positions_mm = ?, notes = ?
                WHERE id = ?
                """,
                (
                    clean_brand,
                    clean_model,
                    eyepiece_type,
                    focal_length_mm,
                    min_focal_length_mm,
                    max_focal_length_mm,
                    apparent_field_deg,
                    afov_min,
                    afov_max,
                    barrel_size,
                    zoom_click_positions_mm,
                    notes,
                    eyepiece_id,
                ),
            )
            connection.commit()
        return True, "Oculare aggiornato."

    def delete_eyepiece(self, eyepiece_id: int, remove_from_profiles: bool = False) -> tuple[bool, str]:
        catalog_id = f"catalog-eyepiece-{eyepiece_id}"
        with closing(self._connect()) as connection:
            if self._is_builtin(connection, "EyepieceCatalog", eyepiece_id):
                return False, "Gli elementi integrati non possono essere eliminati."
            used = self._profile_usage_count(connection, "eyepiece", catalog_id)
            if used and not remove_from_profiles:
                return False, "Questo elemento è utilizzato da uno o più profili."
            if remove_from_profiles:
                self._remove_from_profiles(connection, "eyepiece", catalog_id)
            connection.execute("DELETE FROM EyepieceCatalog WHERE id = ?", (eyepiece_id,))
            connection.commit()
        return True, "Oculare eliminato."

    def barlows(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, multiplier, barrel_size, notes, is_builtin
                FROM BarlowCatalog
                ORDER BY brand, model, multiplier
                """
            ).fetchall()
        return [self._barlow_model(row) for row in rows]

    def add_barlow(self, brand: str, model: str, multiplier: float, barrel_size: str, notes: str = "") -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, "Marca e modello sono obbligatori."
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                "SELECT id FROM BarlowCatalog WHERE brand = ? AND model = ? AND multiplier = ?",
                (clean_brand, clean_model, multiplier),
            ).fetchone()
            if duplicate:
                return False, "Questa Barlow è già presente nel catalogo."
            connection.execute(
                """
                INSERT INTO BarlowCatalog (brand, model, multiplier, barrel_size, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (clean_brand, clean_model, multiplier, barrel_size, notes),
            )
            connection.commit()
        return True, "Barlow aggiunta."

    def update_barlow(self, barlow_id: int, brand: str, model: str, multiplier: float, barrel_size: str, notes: str = "") -> tuple[bool, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_brand or not clean_model:
            return False, "Marca e modello sono obbligatori."
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                """
                SELECT id FROM BarlowCatalog
                WHERE brand = ? AND model = ? AND multiplier = ? AND id <> ?
                """,
                (clean_brand, clean_model, multiplier, barlow_id),
            ).fetchone()
            if duplicate:
                return False, "Questa Barlow è già presente nel catalogo."
            connection.execute(
                """
                UPDATE BarlowCatalog
                SET brand = ?, model = ?, multiplier = ?, barrel_size = ?, notes = ?
                WHERE id = ?
                """,
                (clean_brand, clean_model, multiplier, barrel_size, notes, barlow_id),
            )
            connection.commit()
        return True, "Barlow aggiornata."

    def delete_barlow(self, barlow_id: int, remove_from_profiles: bool = False) -> tuple[bool, str]:
        catalog_id = f"catalog-barlow-{barlow_id}"
        with closing(self._connect()) as connection:
            if self._is_builtin(connection, "BarlowCatalog", barlow_id):
                return False, "Gli elementi integrati non possono essere eliminati."
            used = self._profile_usage_count(connection, "barlow", catalog_id)
            if used and not remove_from_profiles:
                return False, "Questo elemento è utilizzato da uno o più profili."
            if remove_from_profiles:
                self._remove_from_profiles(connection, "barlow", catalog_id)
            connection.execute("DELETE FROM BarlowCatalog WHERE id = ?", (barlow_id,))
            connection.commit()
        return True, "Barlow eliminata."

    def binoculars(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, magnification, objective_diameter_mm,
                       image_stabilized, is_builtin
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
            return False, "Marca e modello sono obbligatori."
        if magnification <= 0 or objective_diameter_mm <= 0:
            return False, "Ingrandimento e diametro obiettivo devono essere maggiori di zero."
        with closing(self._connect()) as connection:
            duplicate = connection.execute(
                """
                SELECT id FROM BinocularCatalog
                WHERE brand = ? AND model = ? AND magnification = ? AND objective_diameter_mm = ?
                """,
                (clean_brand, clean_model, magnification, objective_diameter_mm),
            ).fetchone()
            if duplicate:
                return False, "Questo binocolo è già presente nel catalogo."
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
        return True, "Binocolo aggiunto."

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
            return False, "Marca e modello sono obbligatori."
        if magnification <= 0 or objective_diameter_mm <= 0:
            return False, "Ingrandimento e diametro obiettivo devono essere maggiori di zero."
        with closing(self._connect()) as connection:
            existing = connection.execute(
                "SELECT id FROM BinocularCatalog WHERE id = ?",
                (binocular_id,),
            ).fetchone()
            if not existing:
                return False, "Binocolo non trovato."
            duplicate = connection.execute(
                """
                SELECT id FROM BinocularCatalog
                WHERE brand = ? AND model = ? AND magnification = ? AND objective_diameter_mm = ? AND id <> ?
                """,
                (clean_brand, clean_model, magnification, objective_diameter_mm, binocular_id),
            ).fetchone()
            if duplicate:
                return False, "Questo binocolo è già presente nel catalogo."
            connection.execute(
                """
                UPDATE BinocularCatalog
                SET brand = ?, model = ?, magnification = ?, objective_diameter_mm = ?,
                    image_stabilized = ?
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
        return True, "Binocolo aggiornato."

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
                return False, "Binocolo non trovato."
            if bool(existing["is_builtin"]):
                return False, "Gli elementi integrati non possono essere eliminati."
            used = self._profile_usage_count(connection, "binocular", catalog_id)
            if used and not remove_from_profiles:
                return False, "Questo elemento è utilizzato da uno o più profili."
            if remove_from_profiles:
                self._remove_from_profiles(connection, "binocular", catalog_id)
            connection.execute("DELETE FROM BinocularCatalog WHERE id = ?", (binocular_id,))
            connection.commit()
        return True, "Binocolo eliminato."

    def filters(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, filter_class, barrel_size,
                       central_wavelength_nm, bandwidth_nm, transmission_pct,
                       minimum_aperture_mm, notes, is_builtin
                FROM FilterCatalog
                ORDER BY brand, model, barrel_size
                """
            ).fetchall()
        return [self._filter_model(row) for row in rows]

    def add_filter(
        self,
        brand: str,
        model: str,
        filter_class: str,
        barrel_size: str,
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
            barrel_size,
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
                WHERE brand = ? AND model = ? AND barrel_size = ?
                """,
                values[:2] + (values[3],),
            ).fetchone()
            if duplicate:
                return False, "Questo filtro è già presente nel catalogo."
            connection.execute(
                """
                INSERT INTO FilterCatalog (
                    brand, model, filter_class, barrel_size,
                    central_wavelength_nm, bandwidth_nm, transmission_pct,
                    minimum_aperture_mm, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.commit()
        return True, "Filtro aggiunto."

    def update_filter(
        self,
        filter_id: int,
        brand: str,
        model: str,
        filter_class: str,
        barrel_size: str,
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
            barrel_size,
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
                "SELECT id FROM FilterCatalog WHERE id = ?",
                (filter_id,),
            ).fetchone()
            if not existing:
                return False, "Filtro non trovato."
            duplicate = connection.execute(
                """
                SELECT id FROM FilterCatalog
                WHERE brand = ? AND model = ? AND barrel_size = ? AND id <> ?
                """,
                values[:2] + (values[3], filter_id),
            ).fetchone()
            if duplicate:
                return False, "Questo filtro è già presente nel catalogo."
            connection.execute(
                """
                UPDATE FilterCatalog
                SET brand = ?, model = ?, filter_class = ?, barrel_size = ?,
                    central_wavelength_nm = ?, bandwidth_nm = ?,
                    transmission_pct = ?, minimum_aperture_mm = ?, notes = ?
                WHERE id = ?
                """,
                values + (filter_id,),
            )
            connection.commit()
        return True, "Filtro aggiornato."

    def delete_filter(
        self,
        filter_id: int,
        remove_from_profiles: bool = False,
    ) -> tuple[bool, str]:
        catalog_id = f"catalog-filter-{filter_id}"
        with closing(self._connect()) as connection:
            if self._is_builtin(connection, "FilterCatalog", filter_id):
                return False, "Gli elementi integrati non possono essere eliminati."
            existing = connection.execute(
                "SELECT id FROM FilterCatalog WHERE id = ?",
                (filter_id,),
            ).fetchone()
            if not existing:
                return False, "Filtro non trovato."
            used = self._profile_usage_count(connection, "filter", catalog_id)
            if used and not remove_from_profiles:
                return False, "Questo elemento è utilizzato da uno o più profili."
            if remove_from_profiles:
                self._remove_from_profiles(connection, "filter", catalog_id)
            connection.execute("DELETE FROM FilterCatalog WHERE id = ?", (filter_id,))
            connection.commit()
        return True, "Filtro eliminato."

    def reducers(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, reduction_factor, optical_system,
                       compatible_models, connection, backfocus_mm,
                       visual_compatible, imaging_compatible, corrected_field,
                       notes, is_builtin
                FROM ReducerCatalog
                ORDER BY brand, model, reduction_factor
                """
            ).fetchall()
        return [self._reducer_model(row) for row in rows]

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
            duplicate = connection.execute(
                """
                SELECT id FROM ReducerCatalog
                WHERE brand = ? AND model = ? AND reduction_factor = ?
                """,
                values[:3],
            ).fetchone()
            if duplicate:
                return False, "Questo riduttore è già presente nel catalogo."
            connection.execute(
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
            connection.commit()
        return True, "Riduttore aggiunto."

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
                "SELECT id FROM ReducerCatalog WHERE id = ?",
                (reducer_id,),
            ).fetchone()
            if not existing:
                return False, "Riduttore non trovato."
            duplicate = connection.execute(
                """
                SELECT id FROM ReducerCatalog
                WHERE brand = ? AND model = ? AND reduction_factor = ? AND id <> ?
                """,
                values[:3] + (reducer_id,),
            ).fetchone()
            if duplicate:
                return False, "Questo riduttore è già presente nel catalogo."
            connection.execute(
                """
                UPDATE ReducerCatalog
                SET brand = ?, model = ?, reduction_factor = ?,
                    optical_system = ?, compatible_models = ?, connection = ?,
                    backfocus_mm = ?, visual_compatible = ?,
                    imaging_compatible = ?, corrected_field = ?, notes = ?
                WHERE id = ?
                """,
                values + (reducer_id,),
            )
            connection.commit()
        return True, "Riduttore aggiornato."

    def delete_reducer(
        self,
        reducer_id: int,
        remove_from_profiles: bool = False,
    ) -> tuple[bool, str]:
        catalog_id = f"catalog-reducer-{reducer_id}"
        with closing(self._connect()) as connection:
            if self._is_builtin(connection, "ReducerCatalog", reducer_id):
                return False, "Gli elementi integrati non possono essere eliminati."
            existing = connection.execute(
                "SELECT id FROM ReducerCatalog WHERE id = ?",
                (reducer_id,),
            ).fetchone()
            if not existing:
                return False, "Riduttore non trovato."
            used = self._profile_usage_count(connection, "reducer", catalog_id)
            if used and not remove_from_profiles:
                return False, "Questo elemento è utilizzato da uno o più profili."
            if remove_from_profiles:
                self._remove_from_profiles(connection, "reducer", catalog_id)
            connection.execute("DELETE FROM ReducerCatalog WHERE id = ?", (reducer_id,))
            connection.commit()
        return True, "Riduttore eliminato."

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
                        ("Occhio nudo", "preset:naked-eye"),
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
            "mount_type": row["mount_type"],
            "notes": row["notes"] or "",
            "is_builtin": bool(row["is_builtin"]),
            "catalog_id": f"catalog-telescope-{row['id']}",
            "legacy_catalog_id": f"catalog:{row['brand']}:{row['name']}",
        }

    @staticmethod
    def _eyepiece_model(row: sqlite3.Row) -> dict:
        eyepiece_type = row["eyepiece_type"] or "Fixed"
        min_focal = row["min_focal_length_mm"]
        max_focal = row["max_focal_length_mm"]
        focal_range = f"{min_focal:g}-{max_focal:g} mm" if eyepiece_type == "Zoom" and min_focal and max_focal else f"{row['focal_length_mm']:g} mm"
        return {
            "id": row["id"],
            "catalog_id": f"catalog-eyepiece-{row['id']}",
            "brand": row["brand"],
            "model": row["model"],
            "display_name": f"{row['brand']} {row['model']}",
            "eyepiece_type": eyepiece_type,
            "type": eyepiece_type,
            "focal_length_mm": row["focal_length_mm"],
            "min_focal_length_mm": min_focal,
            "max_focal_length_mm": max_focal,
            "apparent_field_deg": row["apparent_field_deg"],
            "afov_min": row["afov_min"],
            "afov_max": row["afov_max"],
            "barrel_size": row["barrel_size"] or "",
            "zoom_click_positions_mm": row["zoom_click_positions_mm"] or "",
            "notes": row["notes"] or "",
            "focalRangeLabel": focal_range,
            "is_builtin": bool(row["is_builtin"]),
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
            "barrel_size": row["barrel_size"] or "",
            "notes": row["notes"] or "",
            "is_builtin": bool(row["is_builtin"]),
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
            "barrel_size": row["barrel_size"] or "",
            "central_wavelength_nm": row["central_wavelength_nm"],
            "bandwidth_nm": row["bandwidth_nm"],
            "transmission_pct": row["transmission_pct"],
            "minimum_aperture_mm": row["minimum_aperture_mm"],
            "notes": row["notes"] or "",
            "is_builtin": bool(row["is_builtin"]),
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
            "optical_system": optical_system,
            "optical_system_label": OPTICAL_SYSTEM_LABELS.get(
                optical_system,
                optical_system,
            ),
            "compatible_models": row["compatible_models"] or "",
            "connection": row["connection"] or "",
            "backfocus_mm": row["backfocus_mm"],
            "visual_compatible": bool(row["visual_compatible"]),
            "imaging_compatible": bool(row["imaging_compatible"]),
            "corrected_field": bool(row["corrected_field"]),
            "notes": row["notes"] or "",
            "is_builtin": bool(row["is_builtin"]),
        }

    @staticmethod
    def _validated_filter_values(
        brand: str,
        model: str,
        filter_class: str,
        barrel_size: str,
        central_wavelength_nm: float | None,
        bandwidth_nm: float | None,
        transmission_pct: float | None,
        minimum_aperture_mm: int | None,
        notes: str,
    ) -> tuple[tuple, str]:
        clean_brand = brand.strip()
        clean_model = model.strip()
        clean_class = filter_class.strip().upper()
        clean_barrel = barrel_size.strip()
        if not clean_brand or not clean_model or not clean_barrel:
            return (), "Marca, modello e formato sono obbligatori."
        if clean_class not in FILTER_CLASS_LABELS:
            return (), "Tipo di filtro non valido."
        if central_wavelength_nm is not None and central_wavelength_nm <= 0:
            return (), "La lunghezza d'onda deve essere maggiore di zero."
        if bandwidth_nm is not None and bandwidth_nm <= 0:
            return (), "La larghezza di banda deve essere maggiore di zero."
        if transmission_pct is not None and not 0 < transmission_pct <= 100:
            return (), "La trasmissione deve essere compresa tra 0 e 100%."
        if minimum_aperture_mm is not None and minimum_aperture_mm <= 0:
            return (), "L'apertura minima deve essere maggiore di zero."
        return (
            clean_brand,
            clean_model,
            clean_class,
            clean_barrel,
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
            return (), "Marca e modello sono obbligatori."
        if not 0 < reduction_factor < 1:
            return (), "Il fattore di riduzione deve essere compreso tra 0 e 1."
        if clean_system not in OPTICAL_SYSTEM_LABELS:
            return (), "Sistema ottico non valido."
        if backfocus_mm is not None and backfocus_mm <= 0:
            return (), "Il backfocus deve essere maggiore di zero."
        if not visual_compatible and not imaging_compatible:
            return (), "Indica almeno un impiego compatibile."
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
    def _ensure_brand(connection: sqlite3.Connection, brand: str) -> int:
        connection.execute("INSERT OR IGNORE INTO TelescopeBrand (name) VALUES (?)", (brand,))
        row = connection.execute("SELECT id FROM TelescopeBrand WHERE name = ?", (brand,)).fetchone()
        return int(row["id"])

    def _telescope_model_by_id(self, connection: sqlite3.Connection, model_id: int) -> dict | None:
        row = connection.execute(
            """
            SELECT tm.id, tb.name AS brand, tm.name, tm.optical_type,
                   tm.aperture_mm, tm.focal_length_mm, tm.focal_ratio,
                   tm.mount_type, tm.notes, tm.is_builtin
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
            profile_count = connection.execute(
                f"SELECT COUNT(*) FROM EquipmentProfileTelescope WHERE telescope_id IN ({placeholders})",
                ids,
            ).fetchone()[0]
            legacy_count = connection.execute(
                f"SELECT COUNT(*) FROM EquipmentProfile WHERE telescope_id IN ({placeholders})",
                ids,
            ).fetchone()[0]
            return int(profile_count + legacy_count)
        if kind == "eyepiece":
            return int(connection.execute(
                f"SELECT COUNT(*) FROM EquipmentProfileEyepiece WHERE eyepiece_id IN ({placeholders})",
                ids,
            ).fetchone()[0])
        if kind == "barlow":
            return int(connection.execute(
                f"SELECT COUNT(*) FROM EquipmentProfileBarlow WHERE barlow_id IN ({placeholders})",
                ids,
            ).fetchone()[0])
        if kind == "binocular":
            return int(connection.execute(
                f"SELECT COUNT(*) FROM EquipmentProfileBinocular WHERE binocular_id IN ({placeholders})",
                ids,
            ).fetchone()[0])
        if kind == "filter":
            return int(connection.execute(
                f"SELECT COUNT(*) FROM EquipmentProfileFilter WHERE filter_id IN ({placeholders})",
                ids,
            ).fetchone()[0])
        if kind == "reducer":
            return int(connection.execute(
                f"SELECT COUNT(*) FROM EquipmentProfileReducer WHERE reducer_id IN ({placeholders})",
                ids,
            ).fetchone()[0])
        return 0

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
