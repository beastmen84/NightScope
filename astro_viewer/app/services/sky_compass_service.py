from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import NightPlanItem


@dataclass(frozen=True)
class SkyCompassTarget:
    id: str
    name: str
    object_type: str
    direction: str
    score: int
    priority: int
    in_plan: bool
    is_best: bool


class SkyCompassService:
    """Ranks broad observing directions from already prepared Home targets."""

    DIRECTIONS = [
        "Nord",
        "Nord-Est",
        "Est",
        "Sud-Est",
        "Sud",
        "Sud-Ovest",
        "Ovest",
        "Nord-Ovest",
    ]

    @classmethod
    def empty(cls, reason: str, message: str) -> dict:
        return {
            "available": False,
            "reason": reason,
            "message": message,
            "direction": "",
            "targetCount": 0,
            "targetCountLabel": "",
            "targets": [],
            "targetNames": "",
            "alternatives": [],
            "updatedLabel": "",
            "cautionText": "",
        }

    def compass(
        self,
        objects: list[CelestialObject],
        night_plan: list[NightPlanItem],
        best_object: CelestialObject | None,
        *,
        has_location: bool,
        caution_text: str = "",
    ) -> dict:
        if not has_location:
            return self.empty("no_location", "Configura una località per usare Sky Compass.")

        plan_ids = {item.object_id for item in night_plan}
        best_id = best_object.id if best_object else ""
        targets = self._targets(objects, plan_ids, best_id)
        if not targets:
            return self.empty("no_targets", "Nessun target consigliato al momento.")

        grouped = self._group_targets(targets)
        ranked_groups = sorted(
            grouped,
            key=lambda group: (group["directionScore"], group["targetCount"]),
            reverse=True,
        )
        top = ranked_groups[0]
        alternatives = [
            {
                "direction": group["direction"],
                "targetCount": group["targetCount"],
                "targetCountLabel": self._target_count_label(group["targetCount"]),
            }
            for group in ranked_groups[1:3]
            if group["targetCount"] > 0
        ]

        return {
            "available": True,
            "reason": "ready",
            "message": "",
            "direction": top["direction"],
            "targetCount": top["targetCount"],
            "targetCountLabel": self._target_count_label(top["targetCount"]),
            "targets": top["targets"][:4],
            "targetNames": " · ".join(item["name"] for item in top["targets"][:4]),
            "alternatives": alternatives,
            "updatedLabel": "Aggiornato ora",
            "cautionText": caution_text,
        }

    def _targets(self, objects: list[CelestialObject], plan_ids: set[str], best_id: str) -> list[SkyCompassTarget]:
        targets = []
        seen_ids = set()
        for item in objects:
            if item.id in seen_ids or not item.visible:
                continue
            direction = self.normalize_direction(item.direction)
            if not direction:
                continue
            in_plan = item.id in plan_ids
            is_best = item.id == best_id
            priority = item.score + (42 if in_plan else 0) + (58 if is_best else 0)
            targets.append(
                SkyCompassTarget(
                    id=item.id,
                    name=item.name,
                    object_type=item.object_type,
                    direction=direction,
                    score=item.score,
                    priority=priority,
                    in_plan=in_plan,
                    is_best=is_best,
                )
            )
            seen_ids.add(item.id)
        return targets

    def _group_targets(self, targets: list[SkyCompassTarget]) -> list[dict]:
        grouped = {
            direction: {
                "direction": direction,
                "directionScore": 0,
                "targetCount": 0,
                "targets": [],
            }
            for direction in self.DIRECTIONS
        }
        for target in targets:
            group = grouped[target.direction]
            group["directionScore"] += target.priority + 10
            group["targetCount"] += 1
            group["targets"].append(
                {
                    "id": target.id,
                    "name": target.name,
                    "type": target.object_type,
                    "score": target.score,
                    "inPlan": target.in_plan,
                    "isBest": target.is_best,
                }
            )
        for group in grouped.values():
            group["targets"].sort(key=lambda item: (item["isBest"], item["inPlan"], item["score"]), reverse=True)
        return [group for group in grouped.values() if group["targetCount"] > 0]

    @staticmethod
    def normalize_direction(direction: str) -> str:
        normalized = (direction or "").strip().lower().replace("_", "-")
        if not normalized or normalized in {"n/d", "nd", "-", "—"}:
            return ""
        has_north = "nord" in normalized
        has_south = "sud" in normalized
        has_west = "ovest" in normalized
        has_east = "est" in normalized and not has_west
        if has_north and has_east:
            return "Nord-Est"
        if has_south and has_east:
            return "Sud-Est"
        if has_south and has_west:
            return "Sud-Ovest"
        if has_north and has_west:
            return "Nord-Ovest"
        if has_north:
            return "Nord"
        if has_east:
            return "Est"
        if has_south:
            return "Sud"
        if has_west:
            return "Ovest"
        return ""

    @staticmethod
    def _target_count_label(count: int) -> str:
        if count == 1:
            return "1 target consigliato"
        return f"{count} target consigliati"
