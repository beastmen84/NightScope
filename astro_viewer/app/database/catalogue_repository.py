from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path


class CatalogueRepository:
    """SQLite repository for physical targets and their catalogue designations."""

    _OBJECT_COLUMNS = """
        object_id, nome, tipo, costellazione, magnitudine,
        ascensione_retta, declinazione, dimensione_apparente,
        max_angular_size_deg, recommended_observation_type,
        best_filter_class, fallback_filter_class,
        optional_color_filter_class, descrizione
    """

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def list_objects(self, catalogue: str | None = None) -> list[dict]:
        with closing(self._connect()) as connection:
            parameters: tuple[str, ...] = ()
            where_clause = ""
            if catalogue and catalogue.strip():
                where_clause = """
                    WHERE EXISTS (
                        SELECT 1
                        FROM CatalogueDesignation designation
                        WHERE designation.object_id = CatalogueObject.object_id
                          AND LOWER(designation.catalogue) = LOWER(?)
                    )
                """
                parameters = (catalogue.strip(),)
            rows = connection.execute(
                f"""
                SELECT {self._OBJECT_COLUMNS}
                FROM CatalogueObject
                {where_clause}
                """,
                parameters,
            ).fetchall()
            return self._objects_with_designations(connection, rows)

    def get_by_object_id(self, object_id: str) -> dict | None:
        normalized = object_id.strip()
        if not normalized:
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                f"""
                SELECT {self._OBJECT_COLUMNS}
                FROM CatalogueObject
                WHERE LOWER(object_id) = LOWER(?)
                """,
                (normalized,),
            ).fetchone()
            objects = self._objects_with_designations(connection, [row] if row else [])
        return objects[0] if objects else None

    def get_by_designation(self, catalogue: str, designation: str) -> dict | None:
        normalized_catalogue = catalogue.strip()
        normalized_designation = designation.strip()
        if not normalized_catalogue or not normalized_designation:
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                f"""
                SELECT {self._qualified_object_columns('object')}
                FROM CatalogueObject object
                JOIN CatalogueDesignation designation
                  ON designation.object_id = object.object_id
                WHERE LOWER(designation.catalogue) = LOWER(?)
                  AND LOWER(designation.designation) = LOWER(?)
                """,
                (normalized_catalogue, normalized_designation),
            ).fetchone()
            objects = self._objects_with_designations(connection, [row] if row else [])
        return objects[0] if objects else None

    def search(self, query: str, limit: int = 30) -> list[dict]:
        normalized = f"%{query.strip()}%"
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT {self._qualified_object_columns('object')}
                FROM CatalogueObject object
                WHERE object.object_id LIKE ?
                   OR object.nome LIKE ?
                   OR object.tipo LIKE ?
                   OR object.costellazione LIKE ?
                   OR EXISTS (
                       SELECT 1
                       FROM CatalogueDesignation designation
                       WHERE designation.object_id = object.object_id
                         AND (
                             designation.catalogue LIKE ?
                             OR designation.designation LIKE ?
                         )
                   )
                LIMIT ?
                """,
                (normalized,) * 6 + (max(0, int(limit)),),
            ).fetchall()
            return self._objects_with_designations(connection, rows)

    def filter_by_type(self, object_type: str, limit: int = 50) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT {self._OBJECT_COLUMNS}
                FROM CatalogueObject
                WHERE tipo LIKE ?
                ORDER BY magnitudine IS NULL, magnitudine ASC
                LIMIT ?
                """,
                (f"%{object_type.strip()}%", max(0, int(limit))),
            ).fetchall()
            return self._objects_with_designations(connection, rows)

    def catalogues(self) -> list[str]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT DISTINCT catalogue FROM CatalogueDesignation ORDER BY LOWER(catalogue)"
            ).fetchall()
        return [str(row[0]) for row in rows]

    def _objects_with_designations(
        self,
        connection: sqlite3.Connection,
        rows: Iterable[sqlite3.Row],
    ) -> list[dict]:
        objects = [self._row_to_object(row) for row in rows]
        if not objects:
            return []
        object_ids = [item["object_id"] for item in objects]
        placeholders = ", ".join("?" for _ in object_ids)
        designation_rows = connection.execute(
            f"""
            SELECT catalogue, designation, object_id, sort_index, is_primary
            FROM CatalogueDesignation
            WHERE object_id IN ({placeholders})
            ORDER BY is_primary DESC, LOWER(catalogue), sort_index, LOWER(designation)
            """,
            object_ids,
        ).fetchall()
        by_object_id: dict[str, list[dict]] = {object_id: [] for object_id in object_ids}
        for row in designation_rows:
            by_object_id[str(row["object_id"])].append(
                {
                    "catalogue": str(row["catalogue"]),
                    "designation": str(row["designation"]),
                    "sort_index": row["sort_index"],
                    "is_primary": bool(row["is_primary"]),
                }
            )
        for item in objects:
            designations = by_object_id[item["object_id"]]
            primary = next((entry for entry in designations if entry["is_primary"]), None)
            primary = primary or (designations[0] if designations else None)
            item["designations"] = designations
            item["catalogues"] = list(dict.fromkeys(entry["catalogue"] for entry in designations))
            item["primary_catalogue"] = primary["catalogue"] if primary else ""
            item["primary_designation"] = primary["designation"] if primary else ""
            item["primary_sort_index"] = primary["sort_index"] if primary else None
        return sorted(objects, key=self._object_sort_key)

    @classmethod
    def _qualified_object_columns(cls, alias: str) -> str:
        return ", ".join(
            f"{alias}.{column.strip()}"
            for column in cls._OBJECT_COLUMNS.replace("\n", " ").split(",")
            if column.strip()
        )

    @staticmethod
    def _object_sort_key(item: dict) -> tuple[str, int, str, str]:
        sort_index = item.get("primary_sort_index")
        return (
            str(item.get("primary_catalogue", "")).casefold(),
            int(sort_index) if sort_index is not None else 999_999,
            str(item.get("primary_designation", "")).casefold(),
            str(item.get("object_id", "")).casefold(),
        )

    @staticmethod
    def _row_to_object(row: sqlite3.Row) -> dict:
        return {
            "object_id": str(row["object_id"]),
            "name": row["nome"],
            "object_type": row["tipo"],
            "constellation": row["costellazione"],
            "magnitude": row["magnitudine"],
            "ra": row["ascensione_retta"],
            "dec": row["declinazione"],
            "apparent_size": row["dimensione_apparente"],
            "max_angular_size_deg": row["max_angular_size_deg"],
            "recommended_observation_type": row["recommended_observation_type"],
            "best_filter_class": row["best_filter_class"] or "",
            "fallback_filter_class": row["fallback_filter_class"] or "",
            "optional_color_filter_class": row["optional_color_filter_class"] or "",
            "description": row["descrizione"],
        }
