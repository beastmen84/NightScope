from __future__ import annotations

from pathlib import Path

from astro_viewer.app.database.catalogue_repository import CatalogueRepository


class MessierRepository:
    """Temporary compatibility adapter over the generic catalogue repository."""

    def __init__(self, database_path: Path):
        self._catalogue_repository = CatalogueRepository(database_path)

    def list_objects(self) -> list[dict]:
        return [self._messier_projection(item) for item in self._catalogue_repository.list_objects("Messier")]

    def get_by_messier_id(self, messier_id: str) -> dict | None:
        item = self._catalogue_repository.get_by_designation("Messier", messier_id)
        return self._messier_projection(item) if item else None

    def search(self, query: str, limit: int = 30) -> list[dict]:
        return [
            self._messier_projection(item)
            for item in self._catalogue_repository.search(query, limit)
            if "Messier" in item["catalogues"]
        ]

    def filter_by_type(self, object_type: str, limit: int = 50) -> list[dict]:
        return [
            self._messier_projection(item)
            for item in self._catalogue_repository.filter_by_type(object_type, limit)
            if "Messier" in item["catalogues"]
        ]

    @staticmethod
    def _messier_projection(item: dict) -> dict:
        projected = dict(item)
        projected["messier_id"] = item["primary_designation"]
        return projected
