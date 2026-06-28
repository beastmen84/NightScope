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
            "zoneLabel": "",
            "targetCount": 0,
            "targetCountLabel": "",
            "targets": [],
            "primaryTargets": [],
            "otherTargetCount": 0,
            "otherTargetCountLabel": "",
            "decisionReasons": [],
            "alternatives": [],
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
        primary_targets = top["targets"][:3]
        other_target_count = max(0, top["targetCount"] - len(primary_targets))

        return {
            "available": True,
            "reason": "ready",
            "message": "",
            "direction": top["direction"],
            "zoneLabel": "Migliore zona osservativa",
            "targetCount": top["targetCount"],
            "targetCountLabel": self._available_count_label(top["targetCount"]),
            "targets": top["targets"],
            "primaryTargets": primary_targets,
            "otherTargetCount": other_target_count,
            "otherTargetCountLabel": self._other_target_count_label(other_target_count),
            "decisionReasons": self._decision_reasons(top, ranked_groups),
            "alternatives": alternatives,
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
    def _available_count_label(count: int) -> str:
        if count == 1:
            return "1 target osservabile"
        return f"{count} target osservabili"

    @staticmethod
    def _target_count_label(count: int) -> str:
        if count == 1:
            return "1 target consigliato"
        return f"{count} target consigliati"

    def _decision_reasons(self, top_group: dict, ranked_groups: list[dict]) -> list[str]:
        reasons = []
        targets = top_group["targets"]
        if not targets:
            return reasons

        first = targets[0]
        if first["inPlan"]:
            reasons.append("Include un target già nel piano osservativo")
        elif first["isBest"]:
            reasons.append("Presenza del target principale della serata")
        else:
            reasons.append(f"{first['name']} guida la scelta in questa zona")

        deep_sky_count = sum(1 for item in targets if item["type"] != "Pianeta")
        planet_targets = [item for item in targets if item["type"] == "Pianeta"]
        cluster_count = sum(1 for item in targets if self._is_cluster_type(item["type"]))
        if planet_targets and deep_sky_count > 0:
            reasons.append("Pianeti e deep sky nella stessa zona")
        elif cluster_count >= 2:
            reasons.append("Più ammassi osservabili nella stessa zona")
        elif deep_sky_count >= 2:
            reasons.append("Più target deep sky senza spostare il telescopio")
        elif planet_targets and not first["isBest"]:
            reasons.append(f"{planet_targets[0]['name']} è un riferimento planetario utile")

        max_count = max(group["targetCount"] for group in ranked_groups)
        if top_group["targetCount"] == max_count and max_count > 1:
            reasons.append("Maggiore concentrazione di target utili")
        elif top_group["targetCount"] > 1:
            reasons.append("Più target osservabili senza spostare il telescopio")

        return reasons[:3]

    @staticmethod
    def _is_cluster_type(object_type: str) -> bool:
        value = object_type.lower()
        return "ammasso" in value or "cluster" in value

    @staticmethod
    def _other_target_count_label(count: int) -> str:
        if count <= 0:
            return ""
        if count == 1:
            return "+1 altro target"
        return f"+{count} altri target"
