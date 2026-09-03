"""Persist equipment profiles and their catalogue assignments through SQLite.

The repository deliberately uses the existing ``EquipmentProfile`` tables and
catalogue identifiers.  It does not own schema creation or migration, so moving
profile access behind this boundary cannot reset an installed user's profiles.
The transaction-scoped helper functions are shared with catalogue deletions so
removing an item and detaching it from profiles remains one atomic operation.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

NAKED_EYE_CATALOG_ID = "preset:naked-eye"

_CAMERA_ASSIGNMENTS = {
    "astronomy_camera": (
        "EquipmentProfileAstronomyCamera",
        "astronomy_camera_id",
        "catalog-astronomy-camera-",
    ),
    "camera_body": (
        "EquipmentProfileCameraBody",
        "camera_body_id",
        "catalog-camera-body-",
    ),
}

_STRING_ASSIGNMENTS = {
    "eyepiece": ("EquipmentProfileEyepiece", "eyepiece_id"),
    "barlow": ("EquipmentProfileBarlow", "barlow_id"),
    "binocular": ("EquipmentProfileBinocular", "binocular_id"),
    "filter": ("EquipmentProfileFilter", "filter_id"),
    "reducer": ("EquipmentProfileReducer", "reducer_id"),
}


def camera_catalog_database_id(item_id: str, prefix: str) -> int | None:
    """Decode a stable camera catalogue identifier into its positive row ID."""

    normalized = str(item_id or "")
    raw_id = normalized.removeprefix(prefix)
    if not normalized.startswith(prefix) or not raw_id.isdigit():
        return None
    database_id = int(raw_id)
    return database_id if database_id > 0 else None


def profile_usage_count(
        connection: sqlite3.Connection,
        kind: str,
        item_id: str,
        legacy_id: str | None = None,
) -> int:
    """Count profiles using an item on the caller's open transaction."""

    camera_assignment = _CAMERA_ASSIGNMENTS.get(kind)
    if camera_assignment is not None:
        table_name, id_column, prefix = camera_assignment
        database_id = camera_catalog_database_id(item_id, prefix)
        if database_id is None:
            return 0
        return int(
            connection.execute(
                f"""
                SELECT COUNT(DISTINCT assignment.profile_id)
                FROM {table_name} assignment
                JOIN EquipmentProfile profile ON profile.id = assignment.profile_id
                WHERE assignment.{id_column} = ?
                """,
                (database_id,),
            ).fetchone()[0]
        )

    identifiers = [item_id]
    legacy_identifier = legacy_id or ""
    if legacy_identifier and legacy_identifier != item_id:
        identifiers.append(legacy_identifier)
    placeholders = ", ".join("?" for _ in identifiers)
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
        return int(
            connection.execute(
                query,
                [*identifiers, *identifiers],
            ).fetchone()[0]
        )

    assignment = _STRING_ASSIGNMENTS.get(kind)
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
            identifiers,
        ).fetchone()[0]
    )


def remove_item_from_profiles(
        connection: sqlite3.Connection,
        kind: str,
        item_id: str,
        legacy_id: str | None = None,
) -> None:
    """Detach an item without committing the caller's catalogue transaction."""

    identifiers = [item_id]
    legacy_identifier = legacy_id or ""
    if legacy_identifier and legacy_identifier != item_id:
        identifiers.append(legacy_identifier)
    placeholders = ", ".join("?" for _ in identifiers)
    if kind == "telescope":
        connection.execute(
            f"""
            DELETE FROM EquipmentProfileTelescope
            WHERE telescope_id IN ({placeholders})
            """,
            identifiers,
        )
        connection.execute(
            f"""
            UPDATE EquipmentProfile
            SET telescope_id = ?
            WHERE telescope_id IN ({placeholders})
            """,
            [NAKED_EYE_CATALOG_ID, *identifiers],
        )
        return

    assignment = _STRING_ASSIGNMENTS.get(kind)
    if assignment is not None:
        table_name, id_column = assignment
        connection.execute(
            f"DELETE FROM {table_name} WHERE {id_column} IN ({placeholders})",
            identifiers,
        )
        return

    camera_assignment = _CAMERA_ASSIGNMENTS.get(kind)
    if camera_assignment is None:
        return
    table_name, id_column, prefix = camera_assignment
    database_id = camera_catalog_database_id(item_id, prefix)
    if database_id is not None:
        connection.execute(
            f"DELETE FROM {table_name} WHERE {id_column} = ?",
            (database_id,),
        )


class EquipmentProfileRepository:
    """Own profile lifecycle and equipment-assignment persistence."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def profiles(self) -> list[dict]:
        """Return every profile with the active profile first."""

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
        """Make one existing profile active in a single transaction."""

        with closing(self._connect()) as connection:
            connection.execute("UPDATE EquipmentProfile SET active = 0")
            connection.execute(
                "UPDATE EquipmentProfile SET active = 1 WHERE id = ?",
                (profile_id,),
            )
            connection.commit()

    def active_profile(self) -> dict | None:
        """Return the active profile, if the database currently has one."""

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

    def add_profile(
            self,
            profile_name: str,
            telescope_id: str,
            active: bool = False,
    ) -> None:
        """Create or update a profile while retaining its stable database row."""

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
            if profile and telescope_id != NAKED_EYE_CATALOG_ID:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO EquipmentProfileTelescope (
                        profile_id, telescope_id
                    )
                    VALUES (?, ?)
                    """,
                    (profile["id"], telescope_id),
                )
            connection.commit()

    def rename_profile(self, profile_id: int, profile_name: str) -> None:
        """Rename a profile without changing its assignments."""

        with closing(self._connect()) as connection:
            connection.execute(
                "UPDATE EquipmentProfile SET profile_name = ? WHERE id = ?",
                (profile_name, profile_id),
            )
            connection.commit()

    def update_profile_telescope(self, profile_id: int, telescope_id: str) -> None:
        """Update the legacy primary-telescope column retained by the schema."""

        with closing(self._connect()) as connection:
            connection.execute(
                "UPDATE EquipmentProfile SET telescope_id = ? WHERE id = ?",
                (telescope_id, profile_id),
            )
            connection.commit()

    def delete_profile(self, profile_id: int) -> None:
        """Delete one profile and preserve the invariant that an active one exists."""

        with closing(self._connect()) as connection:
            active = connection.execute(
                "SELECT active FROM EquipmentProfile WHERE id = ?",
                (profile_id,),
            ).fetchone()
            connection.execute(
                "DELETE FROM EquipmentProfile WHERE id = ?",
                (profile_id,),
            )
            if active and int(active["active"]) == 1:
                replacement = connection.execute(
                    "SELECT id FROM EquipmentProfile ORDER BY profile_name LIMIT 1"
                ).fetchone()
                if replacement:
                    connection.execute(
                        "UPDATE EquipmentProfile SET active = 1 WHERE id = ?",
                        (replacement["id"],),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO EquipmentProfile (
                            profile_name, active, telescope_id
                        )
                        VALUES (?, 1, ?)
                        """,
                        ("Default", NAKED_EYE_CATALOG_ID),
                    )
            connection.commit()

    def profile_telescope_ids(self, profile_id: int) -> list[str]:
        """Return telescope catalogue IDs assigned to a profile."""

        return self._profile_item_ids(
            "EquipmentProfileTelescope",
            "telescope_id",
            profile_id,
        )

    def profile_full_aperture_solar_filter_telescope_ids(
            self,
            profile_id: int,
    ) -> list[str]:
        """Return assigned telescopes marked with a full-aperture solar filter."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT telescope_id
                FROM EquipmentProfileTelescope
                WHERE profile_id = ?
                  AND has_full_aperture_solar_filter = 1
                ORDER BY telescope_id
                """,
                (profile_id,),
            ).fetchall()
        return [str(row["telescope_id"]) for row in rows]

    def profile_eyepiece_ids(self, profile_id: int) -> list[str]:
        """Return eyepiece catalogue IDs assigned to a profile."""

        return self._profile_item_ids(
            "EquipmentProfileEyepiece",
            "eyepiece_id",
            profile_id,
        )

    def profile_barlow_ids(self, profile_id: int) -> list[str]:
        """Return Barlow catalogue IDs assigned to a profile."""

        return self._profile_item_ids(
            "EquipmentProfileBarlow",
            "barlow_id",
            profile_id,
        )

    def profile_binocular_ids(self, profile_id: int) -> list[str]:
        """Return binocular catalogue IDs assigned to a profile."""

        return self._profile_item_ids(
            "EquipmentProfileBinocular",
            "binocular_id",
            profile_id,
        )

    def profile_filter_ids(self, profile_id: int) -> list[str]:
        """Return filter catalogue IDs assigned to a profile."""

        return self._profile_item_ids(
            "EquipmentProfileFilter",
            "filter_id",
            profile_id,
        )

    def profile_reducer_ids(self, profile_id: int) -> list[str]:
        """Return reducer catalogue IDs assigned to a profile."""

        return self._profile_item_ids(
            "EquipmentProfileReducer",
            "reducer_id",
            profile_id,
        )

    def profile_astronomy_camera_ids(self, profile_id: int) -> list[str]:
        """Return astronomy-camera catalogue IDs assigned to a profile."""

        return self._profile_camera_item_ids(
            "EquipmentProfileAstronomyCamera",
            "astronomy_camera_id",
            "catalog-astronomy-camera-",
            profile_id,
        )

    def profile_camera_body_ids(self, profile_id: int) -> list[str]:
        """Return camera-body catalogue IDs assigned to a profile."""

        return self._profile_camera_item_ids(
            "EquipmentProfileCameraBody",
            "camera_body_id",
            "catalog-camera-body-",
            profile_id,
        )

    def assign_profile_telescope(self, profile_id: int, telescope_id: str) -> None:
        """Assign a telescope to a profile without duplicating the row."""

        self._assign_profile_item(
            "EquipmentProfileTelescope",
            "telescope_id",
            profile_id,
            telescope_id,
        )

    def set_profile_full_aperture_solar_filter(
            self,
            profile_id: int,
            telescope_id: str,
            available: bool,
    ) -> bool:
        """Update solar-filter availability for an existing telescope assignment."""

        with closing(self._connect()) as connection:
            cursor = connection.execute(
                """
                UPDATE EquipmentProfileTelescope
                SET has_full_aperture_solar_filter = ?
                WHERE profile_id = ? AND telescope_id = ?
                """,
                (1 if available else 0, profile_id, telescope_id),
            )
            connection.commit()
        return cursor.rowcount == 1

    def remove_profile_telescope(self, profile_id: int, telescope_id: str) -> None:
        """Remove a telescope assignment from a profile."""

        self._remove_profile_item(
            "EquipmentProfileTelescope",
            "telescope_id",
            profile_id,
            telescope_id,
        )

    def assign_profile_eyepiece(self, profile_id: int, eyepiece_id: str) -> None:
        """Assign an eyepiece to a profile."""

        self._assign_profile_item(
            "EquipmentProfileEyepiece",
            "eyepiece_id",
            profile_id,
            eyepiece_id,
        )

    def remove_profile_eyepiece(self, profile_id: int, eyepiece_id: str) -> None:
        """Remove an eyepiece assignment from a profile."""

        self._remove_profile_item(
            "EquipmentProfileEyepiece",
            "eyepiece_id",
            profile_id,
            eyepiece_id,
        )

    def assign_profile_barlow(self, profile_id: int, barlow_id: str) -> None:
        """Assign a Barlow to a profile."""

        self._assign_profile_item(
            "EquipmentProfileBarlow",
            "barlow_id",
            profile_id,
            barlow_id,
        )

    def remove_profile_barlow(self, profile_id: int, barlow_id: str) -> None:
        """Remove a Barlow assignment from a profile."""

        self._remove_profile_item(
            "EquipmentProfileBarlow",
            "barlow_id",
            profile_id,
            barlow_id,
        )

    def assign_profile_binocular(self, profile_id: int, binocular_id: str) -> None:
        """Assign a binocular to a profile."""

        self._assign_profile_item(
            "EquipmentProfileBinocular",
            "binocular_id",
            profile_id,
            binocular_id,
        )

    def remove_profile_binocular(self, profile_id: int, binocular_id: str) -> None:
        """Remove a binocular assignment from a profile."""

        self._remove_profile_item(
            "EquipmentProfileBinocular",
            "binocular_id",
            profile_id,
            binocular_id,
        )

    def assign_profile_filter(self, profile_id: int, filter_id: str) -> None:
        """Assign a filter to a profile."""

        self._assign_profile_item(
            "EquipmentProfileFilter",
            "filter_id",
            profile_id,
            filter_id,
        )

    def remove_profile_filter(self, profile_id: int, filter_id: str) -> None:
        """Remove a filter assignment from a profile."""

        self._remove_profile_item(
            "EquipmentProfileFilter",
            "filter_id",
            profile_id,
            filter_id,
        )

    def assign_profile_reducer(self, profile_id: int, reducer_id: str) -> None:
        """Assign a focal reducer to a profile."""

        self._assign_profile_item(
            "EquipmentProfileReducer",
            "reducer_id",
            profile_id,
            reducer_id,
        )

    def remove_profile_reducer(self, profile_id: int, reducer_id: str) -> None:
        """Remove a focal-reducer assignment from a profile."""

        self._remove_profile_item(
            "EquipmentProfileReducer",
            "reducer_id",
            profile_id,
            reducer_id,
        )

    def assign_profile_astronomy_camera(
            self,
            profile_id: int,
            camera_id: str,
    ) -> None:
        """Assign an astronomy camera by its stable catalogue identifier."""

        self._assign_profile_camera_item(
            "EquipmentProfileAstronomyCamera",
            "astronomy_camera_id",
            "catalog-astronomy-camera-",
            profile_id,
            camera_id,
        )

    def remove_profile_astronomy_camera(
            self,
            profile_id: int,
            camera_id: str,
    ) -> None:
        """Remove an astronomy-camera assignment."""

        self._remove_profile_camera_item(
            "EquipmentProfileAstronomyCamera",
            "astronomy_camera_id",
            "catalog-astronomy-camera-",
            profile_id,
            camera_id,
        )

    def assign_profile_camera_body(
            self,
            profile_id: int,
            camera_id: str,
    ) -> None:
        """Assign a camera body by its stable catalogue identifier."""

        self._assign_profile_camera_item(
            "EquipmentProfileCameraBody",
            "camera_body_id",
            "catalog-camera-body-",
            profile_id,
            camera_id,
        )

    def remove_profile_camera_body(
            self,
            profile_id: int,
            camera_id: str,
    ) -> None:
        """Remove a camera-body assignment."""

        self._remove_profile_camera_item(
            "EquipmentProfileCameraBody",
            "camera_body_id",
            "catalog-camera-body-",
            profile_id,
            camera_id,
        )

    def profile_usage_count(self, kind: str, item_id: str) -> int:
        """Count profiles using one stable catalogue identifier."""

        with closing(self._connect()) as connection:
            return profile_usage_count(connection, kind, item_id)

    def _profile_item_ids(
            self,
            table: str,
            id_column: str,
            profile_id: int,
    ) -> list[str]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT {id_column}
                FROM {table}
                WHERE profile_id = ?
                ORDER BY {id_column}
                """,
                (profile_id,),
            ).fetchall()
        return [row[id_column] for row in rows]

    def _profile_camera_item_ids(
            self,
            table: str,
            id_column: str,
            prefix: str,
            profile_id: int,
    ) -> list[str]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT {id_column}
                FROM {table}
                WHERE profile_id = ?
                ORDER BY {id_column}
                """,
                (profile_id,),
            ).fetchall()
        return [f"{prefix}{int(row[id_column])}" for row in rows]

    def _assign_profile_item(
            self,
            table: str,
            id_column: str,
            profile_id: int,
            item_id: str | int,
    ) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                f"""
                INSERT OR IGNORE INTO {table} (profile_id, {id_column})
                VALUES (?, ?)
                """,
                (profile_id, item_id),
            )
            connection.commit()

    def _remove_profile_item(
            self,
            table: str,
            id_column: str,
            profile_id: int,
            item_id: str | int,
    ) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                f"""
                DELETE FROM {table}
                WHERE profile_id = ? AND {id_column} = ?
                """,
                (profile_id, item_id),
            )
            connection.commit()

    def _assign_profile_camera_item(
            self,
            table: str,
            id_column: str,
            prefix: str,
            profile_id: int,
            item_id: str,
    ) -> None:
        database_id = self._camera_catalog_database_id(item_id, prefix)
        if database_id is None:
            return
        self._assign_profile_item(
            table,
            id_column,
            profile_id,
            database_id,
        )

    def _remove_profile_camera_item(
            self,
            table: str,
            id_column: str,
            prefix: str,
            profile_id: int,
            item_id: str,
    ) -> None:
        database_id = self._camera_catalog_database_id(item_id, prefix)
        if database_id is None:
            return
        self._remove_profile_item(
            table,
            id_column,
            profile_id,
            database_id,
        )

    @staticmethod
    def _camera_catalog_database_id(item_id: str, prefix: str) -> int | None:
        return camera_catalog_database_id(item_id, prefix)
