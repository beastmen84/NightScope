from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace

from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
)


@dataclass(frozen=True)
class SkyCompassTarget:
    id: str
    name: str
    object_type: str
    direction: str
    display_score: int
    observable_value: float
    direction_score_contribution: float
    in_plan: bool
    is_best: bool


class SkyCompassService:
    """Ranks current directions with NSOM and a geometry-only fallback."""

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
    TARGET_PRESENCE_BONUS = 10.0

    @classmethod
    def empty(cls, reason: str, message: str, *, caution_text: str = "") -> dict:
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
            "cautionText": caution_text,
        }

    def compass(
        self,
        objects: list[CelestialObject],
        night_plan: list[NightPlanItem],
        best_object: CelestialObject | None,
        *,
        has_location: bool,
        caution_text: str = "",
        condition_inputs: ObservationConditionInputs | None = None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None = None,
        observable_objects_by_id: Mapping[str, CelestialObject] | None = None,
    ) -> dict:
        if not has_location:
            return self.empty(
                "no_location",
                "Configura una località per usare Sky Compass.",
                caution_text=caution_text,
            )

        plan_ids = {item.object_id for item in night_plan}
        best_id = best_object.id if best_object else ""
        targets = self._targets(
            objects,
            plan_ids,
            best_id,
            condition_inputs=condition_inputs,
            moon_geometry_by_object_id=moon_geometry_by_object_id,
            observable_objects_by_id=observable_objects_by_id,
        )
        if not targets:
            return self.empty(
                "no_targets",
                "Nessun target osservabile in questo momento.",
                caution_text=caution_text,
            )

        grouped = self._group_targets(targets)
        ranked_groups = sorted(
            grouped,
            key=lambda group: (
                group["directionScore"],
                group["targetCount"],
                -self.DIRECTIONS.index(group["direction"]),
            ),
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
        ]
        primary_targets = top["targets"][:3]
        other_target_count = max(0, top["targetCount"] - len(primary_targets))
        return {
            "available": True,
            "reason": "ready",
            "message": "",
            "direction": top["direction"],
            "zoneLabel": "Migliore zona adesso",
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

    def _targets(
        self,
        objects: list[CelestialObject],
        plan_ids: set[str],
        best_id: str,
        *,
        condition_inputs: ObservationConditionInputs | None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None,
        observable_objects_by_id: Mapping[str, CelestialObject] | None,
    ) -> list[SkyCompassTarget]:
        targets = []
        seen_ids = set()
        observable_objects = observable_objects_by_id or {}
        use_nsom = condition_inputs is not None
        for item in objects:
            if item.id in seen_ids or not item.visible or not self.is_observable_now(item):
                continue
            direction = self.normalize_direction(item.direction)
            if not direction:
                continue
            altitude_factor = self.current_altitude_factor(item)
            if use_nsom:
                observable_item = observable_objects.get(item.id, item)
                observable_value = build_home_observable_target_value(
                    observable_item,
                    condition_inputs=replace(
                        condition_inputs,
                        moon_geometry=(moon_geometry_by_object_id or {}).get(item.id),
                    ),
                ).value
            else:
                observable_value = float(item.score)
            targets.append(
                SkyCompassTarget(
                    id=item.id,
                    name=item.name,
                    object_type=item.object_type,
                    direction=direction,
                    display_score=item.score,
                    observable_value=observable_value,
                    direction_score_contribution=(
                        observable_value * altitude_factor
                    )
                    + self.TARGET_PRESENCE_BONUS,
                    in_plan=item.id in plan_ids,
                    is_best=item.id == best_id,
                )
            )
            seen_ids.add(item.id)
        return targets

    def _group_targets(self, targets: list[SkyCompassTarget]) -> list[dict]:
        grouped = {
            direction: {
                "direction": direction,
                "directionScore": 0.0,
                "targetCount": 0,
                "_targets": [],
            }
            for direction in self.DIRECTIONS
        }
        for target in targets:
            group = grouped[target.direction]
            group["directionScore"] += target.direction_score_contribution
            group["targetCount"] += 1
            group["_targets"].append(
                (
                    {
                        "id": target.id,
                        "name": target.name,
                        "type": target.object_type,
                        "score": target.display_score,
                        "inPlan": target.in_plan,
                        "isBest": target.is_best,
                    },
                    target.observable_value,
                    target.direction_score_contribution,
                )
            )
        for group in grouped.values():
            ranked_targets = sorted(
                group["_targets"],
                key=lambda row: (
                    row[2],
                    row[1],
                    row[0]["isBest"],
                    row[0]["inPlan"],
                    row[0]["score"],
                ),
                reverse=True,
            )
            group["targets"] = [row[0] for row in ranked_targets]
            del group["_targets"]
        return [group for group in grouped.values() if group["targetCount"] > 0]

    @staticmethod
    def is_observable_now(item: CelestialObject) -> bool:
        return item.observable_now is not False

    @staticmethod
    def current_altitude_factor(item: CelestialObject) -> float:
        altitude = item.current_altitude_degrees
        if altitude is None:
            match = re.search(r"-?\d+(?:[.,]\d+)?", item.current_altitude or "")
            if not match:
                return 1.0
            altitude = float(match.group(0).replace(",", "."))
        threshold = 8.0 if item.object_type == "Pianeta" else 15.0
        normalized = max(0.0, min(1.0, (altitude - threshold) / (60.0 - threshold)))
        return 0.35 + (0.65 * normalized)

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
        return "1 target osservabile ora" if count == 1 else f"{count} target osservabili ora"

    _target_count_label = _available_count_label

    def _decision_reasons(self, top_group: dict, ranked_groups: list[dict]) -> list[str]:
        reasons = []
        targets = top_group["targets"]
        if not targets:
            return reasons
        first = targets[0]
        reasons.append(f"{first['name']} guida la scelta in questo momento")

        deep_sky_count = sum(1 for item in targets if item["type"] != "Pianeta")
        planet_targets = [item for item in targets if item["type"] == "Pianeta"]
        cluster_count = sum(1 for item in targets if self._is_cluster_type(item["type"]))
        if planet_targets and deep_sky_count > 0:
            reasons.append("Pianeti e deep sky nella stessa zona")
        elif cluster_count >= 2:
            reasons.append("Più ammassi nella stessa zona")
        elif deep_sky_count >= 2:
            reasons.append("Più target deep sky nella stessa zona")
        elif planet_targets and not first["isBest"]:
            reasons.append(f"{planet_targets[0]['name']} è il riferimento planetario della zona")

        max_count = max(group["targetCount"] for group in ranked_groups)
        if top_group["targetCount"] == max_count and max_count > 1:
            reasons.append("Maggiore concentrazione di target osservabili ora")
        elif top_group["targetCount"] > 1:
            reasons.append("Più target osservabili ora nella stessa zona")
        if any(item["inPlan"] for item in targets):
            reasons.append("Include una tappa del piano attualmente osservabile")
        return reasons[:3]

    @staticmethod
    def _is_cluster_type(object_type: str) -> bool:
        value = object_type.lower()
        return "ammasso" in value or "cluster" in value

    @staticmethod
    def _other_target_count_label(count: int) -> str:
        if count <= 0:
            return ""
        return "+1 altro target" if count == 1 else f"+{count} altri target"
