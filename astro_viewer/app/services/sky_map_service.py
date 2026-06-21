from __future__ import annotations

from astro_viewer.app.models.observing import CelestialObject


class SkyMapService:
    """Groups visible targets by simple cardinal directions."""

    DIRECTIONS = ["Nord", "Est", "Sud", "Ovest"]

    def map_targets(self, objects: list[CelestialObject]) -> list[dict]:
        grouped = {direction: [] for direction in self.DIRECTIONS}
        for item in objects:
            if not item.visible:
                continue
            direction = self._normalize_direction(item.direction)
            grouped[direction].append(
                {
                    "id": item.id,
                    "name": item.name,
                    "type": item.object_type,
                    "altitude": item.current_altitude,
                    "score": item.score,
                    "image": item.image,
                }
            )
        return [
            {
                "direction": direction,
                "targets": sorted(grouped[direction], key=lambda item: item["score"], reverse=True)[:5],
            }
            for direction in self.DIRECTIONS
        ]

    @staticmethod
    def _normalize_direction(direction: str) -> str:
        if "Sud" in direction:
            return "Sud"
        if "Est" in direction:
            return "Est"
        if "Ovest" in direction:
            return "Ovest"
        return "Nord"

