from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from astro_viewer.app.models.equipment import Barlow, Eyepiece, Telescope


class EquipmentCatalogRepository:
    """SQLite access for telescope, eyepiece, Barlow and equipment profile catalogs."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def brands(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id, name FROM TelescopeBrand ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def models(self, brand_id: int | None = None) -> list[dict]:
        query = """
            SELECT tm.id, tb.name AS brand, tm.name, tm.optical_type,
                   tm.aperture_mm, tm.focal_length_mm, tm.focal_ratio,
                   tm.mount_type, tm.notes
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

    def eyepieces(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, focal_length_mm, apparent_field_deg, barrel_size, notes
                FROM EyepieceCatalog
                ORDER BY brand, model, focal_length_mm
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def barlows(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, brand, model, multiplier, barrel_size, notes
                FROM BarlowCatalog
                ORDER BY brand, model, multiplier
                """
            ).fetchall()
        return [dict(row) for row in rows]

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

    def owned_telescopes(self) -> list[Telescope]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, name, aperture_mm, focal_length_mm, optical_type, mount
                FROM OwnedTelescope
                ORDER BY name
                """
            ).fetchall()
        return [
            Telescope(
                id=row["id"],
                name=row["name"],
                aperture_mm=int(row["aperture_mm"]),
                focal_length_mm=int(row["focal_length_mm"]),
                optical_type=row["optical_type"],
                mount=row["mount"],
            )
            for row in rows
        ]

    def save_owned_telescope(self, telescope: Telescope, source_catalog_id: str = "") -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO OwnedTelescope (
                    id, name, aperture_mm, focal_length_mm, optical_type, mount, source_catalog_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    aperture_mm = excluded.aperture_mm,
                    focal_length_mm = excluded.focal_length_mm,
                    optical_type = excluded.optical_type,
                    mount = excluded.mount,
                    source_catalog_id = excluded.source_catalog_id
                """,
                (
                    telescope.id,
                    telescope.name,
                    telescope.aperture_mm,
                    telescope.focal_length_mm,
                    telescope.optical_type,
                    telescope.mount,
                    source_catalog_id,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                ),
            )
            connection.commit()

    def delete_owned_telescope(self, telescope_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute("DELETE FROM EquipmentProfileTelescope WHERE telescope_id = ?", (telescope_id,))
            connection.execute("DELETE FROM OwnedTelescope WHERE id = ?", (telescope_id,))
            connection.execute(
                "UPDATE EquipmentProfile SET telescope_id = ? WHERE telescope_id = ?",
                ("preset:naked-eye", telescope_id),
            )
            connection.commit()

    def owned_eyepieces(self) -> list[Eyepiece]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, name, focal_length_mm, apparent_field_deg, barrel_size,
                       eyepiece_type, min_focal_length_mm, max_focal_length_mm
                FROM OwnedEyepiece
                ORDER BY name
                """
            ).fetchall()
        return [
            Eyepiece(
                id=row["id"],
                name=row["name"],
                focal_length_mm=float(row["focal_length_mm"]),
                apparent_field_deg=float(row["apparent_field_deg"]),
                barrel_size=row["barrel_size"] or "",
                eyepiece_type=row["eyepiece_type"] or "Fixed",
                min_focal_length_mm=float(row["min_focal_length_mm"]) if row["min_focal_length_mm"] is not None else None,
                max_focal_length_mm=float(row["max_focal_length_mm"]) if row["max_focal_length_mm"] is not None else None,
            )
            for row in rows
        ]

    def save_owned_eyepiece(self, eyepiece: Eyepiece, source_catalog_id: str = "") -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO OwnedEyepiece (
                    id, name, focal_length_mm, apparent_field_deg, barrel_size, eyepiece_type,
                    min_focal_length_mm, max_focal_length_mm, source_catalog_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    focal_length_mm = excluded.focal_length_mm,
                    apparent_field_deg = excluded.apparent_field_deg,
                    barrel_size = excluded.barrel_size,
                    eyepiece_type = excluded.eyepiece_type,
                    min_focal_length_mm = excluded.min_focal_length_mm,
                    max_focal_length_mm = excluded.max_focal_length_mm,
                    source_catalog_id = excluded.source_catalog_id
                """,
                (
                    eyepiece.id,
                    eyepiece.name,
                    eyepiece.focal_length_mm,
                    eyepiece.apparent_field_deg,
                    eyepiece.barrel_size,
                    eyepiece.eyepiece_type,
                    eyepiece.min_focal_length_mm,
                    eyepiece.max_focal_length_mm,
                    source_catalog_id,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                ),
            )
            connection.commit()

    def delete_owned_eyepiece(self, eyepiece_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute("DELETE FROM EquipmentProfileEyepiece WHERE eyepiece_id = ?", (eyepiece_id,))
            connection.execute("DELETE FROM OwnedEyepiece WHERE id = ?", (eyepiece_id,))
            connection.commit()

    def owned_barlows(self) -> list[Barlow]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, name, multiplier, barrel_size
                FROM OwnedBarlow
                ORDER BY name
                """
            ).fetchall()
        return [
            Barlow(
                id=row["id"],
                name=row["name"],
                multiplier=float(row["multiplier"]),
                barrel_size=row["barrel_size"] or "",
            )
            for row in rows
        ]

    def save_owned_barlow(self, barlow: Barlow, source_catalog_id: str = "") -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO OwnedBarlow (id, name, multiplier, barrel_size, source_catalog_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    multiplier = excluded.multiplier,
                    barrel_size = excluded.barrel_size,
                    source_catalog_id = excluded.source_catalog_id
                """,
                (
                    barlow.id,
                    barlow.name,
                    barlow.multiplier,
                    barlow.barrel_size,
                    source_catalog_id,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                ),
            )
            connection.commit()

    def delete_owned_barlow(self, barlow_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute("DELETE FROM EquipmentProfileBarlow WHERE barlow_id = ?", (barlow_id,))
            connection.execute("DELETE FROM OwnedBarlow WHERE id = ?", (barlow_id,))
            connection.commit()

    def profile_telescope_ids(self, profile_id: int) -> list[str]:
        return self._profile_item_ids("EquipmentProfileTelescope", "telescope_id", profile_id)

    def profile_eyepiece_ids(self, profile_id: int) -> list[str]:
        return self._profile_item_ids("EquipmentProfileEyepiece", "eyepiece_id", profile_id)

    def profile_barlow_ids(self, profile_id: int) -> list[str]:
        return self._profile_item_ids("EquipmentProfileBarlow", "barlow_id", profile_id)

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
            connection.execute(
                "UPDATE EquipmentProfile SET profile_name = ? WHERE id = ?",
                (profile_name, profile_id),
            )
            connection.commit()

    def update_profile_telescope(self, profile_id: int, telescope_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                "UPDATE EquipmentProfile SET telescope_id = ? WHERE id = ?",
                (telescope_id, profile_id),
            )
            connection.commit()

    def delete_profile(self, profile_id: int) -> None:
        with closing(self._connect()) as connection:
            active = connection.execute(
                "SELECT active FROM EquipmentProfile WHERE id = ?",
                (profile_id,),
            ).fetchone()
            connection.execute("DELETE FROM EquipmentProfile WHERE id = ?", (profile_id,))
            if active and int(active["active"]) == 1:
                replacement = connection.execute(
                    "SELECT id FROM EquipmentProfile ORDER BY profile_name LIMIT 1"
                ).fetchone()
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

    def model_by_catalog_id(self, telescope_id: str) -> dict | None:
        parts = telescope_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "catalog":
            return None
        brand, model = parts[1], parts[2]
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT tm.id, tb.name AS brand, tm.name, tm.optical_type,
                       tm.aperture_mm, tm.focal_length_mm, tm.focal_ratio,
                       tm.mount_type, tm.notes
                FROM TelescopeModel tm
                JOIN TelescopeBrand tb ON tb.id = tm.brand_id
                WHERE tb.name = ? AND tm.name = ?
                LIMIT 1
                """,
                (brand, model),
            ).fetchone()
        return self._telescope_model(row) if row else None

    @staticmethod
    def _telescope_model(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "brand": row["brand"],
            "name": row["name"],
            "optical_type": row["optical_type"],
            "aperture_mm": row["aperture_mm"],
            "focal_length_mm": row["focal_length_mm"],
            "focal_ratio": row["focal_ratio"],
            "mount_type": row["mount_type"],
            "notes": row["notes"],
            "catalog_id": f"catalog:{row['brand']}:{row['name']}",
        }

    def _profile_item_ids(self, table: str, id_column: str, profile_id: int) -> list[str]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"SELECT {id_column} FROM {table} WHERE profile_id = ? ORDER BY {id_column}",
                (profile_id,),
            ).fetchall()
        return [row[id_column] for row in rows]

    def _assign_profile_item(self, table: str, id_column: str, profile_id: int, item_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                f"INSERT OR IGNORE INTO {table} (profile_id, {id_column}) VALUES (?, ?)",
                (profile_id, item_id),
            )
            connection.commit()

    def _remove_profile_item(self, table: str, id_column: str, profile_id: int, item_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                f"DELETE FROM {table} WHERE profile_id = ? AND {id_column} = ?",
                (profile_id, item_id),
            )
            connection.commit()
