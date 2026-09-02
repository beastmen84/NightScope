from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace

from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.services.catalogue_presentation import catalogue_object_type_label
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
from astro_viewer.app.services.direction_presentation import direction_code, direction_label
from astro_viewer.app.services.localization import tr
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
)


@dataclass(frozen=True)
class SkyCompassTarget:
    id: str
    name: str
    object_type: str
    object_type_code: str
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
    LIVE_SWITCH_CONFIRMATIONS = 5
    LIVE_SWITCH_MARGIN_RATIO = 0.15
    LIVE_SWITCH_MIN_SCORE_DELTA = 5.0

    def __init__(self) -> None:
        self._live_direction = ""
        self._pending_live_direction = ""
        self._pending_live_confirmations = 0

    def reset_live_direction_stability(self) -> None:
        self._live_direction = ""
        self._clear_pending_live_direction()

    @classmethod
    def empty(cls, reason: str, message: str, *, caution_text: str = "") -> dict:
        return {
            "available": False,
            "reason": reason,
            "message": message,
            "direction": "",
            "directionCode": "",
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
        return self._compass(
            objects,
            night_plan,
            best_object,
            has_location=has_location,
            caution_text=caution_text,
            condition_inputs=condition_inputs,
            moon_geometry_by_object_id=moon_geometry_by_object_id,
            observable_objects_by_id=observable_objects_by_id,
            stabilize_live_direction=False,
        )

    def live_compass(
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
        """Build a live payload while suppressing marginal direction churn."""
        return self._compass(
            objects,
            night_plan,
            best_object,
            has_location=has_location,
            caution_text=caution_text,
            condition_inputs=condition_inputs,
            moon_geometry_by_object_id=moon_geometry_by_object_id,
            observable_objects_by_id=observable_objects_by_id,
            stabilize_live_direction=True,
        )

    def _compass(
        self,
        objects: list[CelestialObject],
        night_plan: list[NightPlanItem],
        best_object: CelestialObject | None,
        *,
        has_location: bool,
        caution_text: str,
        condition_inputs: ObservationConditionInputs | None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None,
        observable_objects_by_id: Mapping[str, CelestialObject] | None,
        stabilize_live_direction: bool,
    ) -> dict:
        if not has_location:
            if stabilize_live_direction:
                self.reset_live_direction_stability()
            return self.empty(
                "no_location",
                tr("Configura una località per usare Sky Compass."),
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
            if stabilize_live_direction:
                self.reset_live_direction_stability()
            return self.empty(
                "no_targets",
                tr("Nessun oggetto osservabile in questo momento."),
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
        top = (
            self._stable_live_group(ranked_groups)
            if stabilize_live_direction
            else ranked_groups[0]
        )
        alternative_groups = [
            group
            for group in ranked_groups
            if group["direction"] != top["direction"]
        ][:2]
        alternatives = [
            {
                "directionCode": direction_code(group["direction"]),
                "direction": direction_label(group["direction"]),
                "targetCount": group["targetCount"],
                "targetCountLabel": self._target_count_label(group["targetCount"]),
            }
            for group in alternative_groups
        ]
        primary_targets = top["targets"][:3]
        other_target_count = max(0, top["targetCount"] - len(primary_targets))
        return {
            "available": True,
            "reason": "ready",
            "message": "",
            "directionCode": direction_code(top["direction"]),
            "direction": direction_label(top["direction"]),
            "zoneLabel": tr("Migliore zona adesso"),
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

    def _stable_live_group(self, ranked_groups: list[dict]) -> dict:
        challenger = ranked_groups[0]
        groups_by_direction = {
            group["direction"]: group
            for group in ranked_groups
        }
        current = groups_by_direction.get(self._live_direction)
        if current is None:
            self._accept_live_direction(challenger["direction"])
            return challenger

        if challenger["direction"] == current["direction"]:
            self._clear_pending_live_direction()
            return current

        if self._has_decisive_live_margin(challenger, current):
            self._accept_live_direction(challenger["direction"])
            return challenger

        if self._pending_live_direction == challenger["direction"]:
            self._pending_live_confirmations += 1
        else:
            self._pending_live_direction = challenger["direction"]
            self._pending_live_confirmations = 1

        if self._pending_live_confirmations >= self.LIVE_SWITCH_CONFIRMATIONS:
            self._accept_live_direction(challenger["direction"])
            return challenger
        return current

    def _has_decisive_live_margin(self, challenger: dict, current: dict) -> bool:
        current_score = float(current["directionScore"])
        score_delta = float(challenger["directionScore"]) - current_score
        required_delta = max(
            self.LIVE_SWITCH_MIN_SCORE_DELTA,
            abs(current_score) * self.LIVE_SWITCH_MARGIN_RATIO,
        )
        return score_delta >= required_delta

    def _accept_live_direction(self, direction: str) -> None:
        self._live_direction = direction
        self._clear_pending_live_direction()

    def _clear_pending_live_direction(self) -> None:
        self._pending_live_direction = ""
        self._pending_live_confirmations = 0

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
            canonical_id = item.id.strip().casefold()
            if (
                (canonical_id and canonical_id in seen_ids)
                or not item.visible
                or not self.is_observable_now(item)
            ):
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
                    object_type_code=self.object_type_code(item),
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
            if canonical_id:
                seen_ids.add(canonical_id)
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
                        "typeLabel": catalogue_object_type_label(target.object_type),
                        "typeCode": target.object_type_code,
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
    def object_type_code(item: CelestialObject) -> str:
        if item.id in {
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
        }:
            return "planet"
        value = str(item.object_type or "").casefold()
        if "galaxy" in value or "galass" in value:
            return "galaxy"
        if "nebula" in value or "nebul" in value:
            return "nebula"
        if "globular" in value or "globulare" in value:
            return "globular_cluster"
        if "cluster" in value or "ammasso" in value:
            return "open_cluster"
        if "planet" in value or "pianeta" in value:
            return "planet"
        return "target"

    @staticmethod
    def current_altitude_factor(item: CelestialObject) -> float:
        altitude = item.current_altitude_degrees
        if altitude is None:
            match = re.search(r"-?\d+(?:[.,]\d+)?", item.current_altitude or "")
            if not match:
                return 1.0
            altitude = float(match.group(0).replace(",", "."))
        threshold = 8.0 if SkyCompassService.object_type_code(item) == "planet" else 15.0
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
        return (
            tr("1 oggetto osservabile ora")
            if count == 1
            else tr("{count} oggetti osservabili ora", count=count)
        )

    _target_count_label = _available_count_label

    def _decision_reasons(self, top_group: dict, ranked_groups: list[dict]) -> list[str]:
        reasons = []
        targets = top_group["targets"]
        if not targets:
            return reasons
        first = targets[0]
        reasons.append(
            tr(
                "{name} guida la scelta in questo momento",
                name=first["name"],
            )
        )

        deep_sky_count = sum(1 for item in targets if item["typeCode"] != "planet")
        planet_targets = [item for item in targets if item["typeCode"] == "planet"]
        cluster_count = sum(
            1
            for item in targets
            if item["typeCode"] in {"globular_cluster", "open_cluster"}
        )
        if planet_targets and deep_sky_count > 0:
            reasons.append(tr("Pianeti e deep sky nella stessa zona"))
        elif cluster_count >= 2:
            reasons.append(tr("Più ammassi nella stessa zona"))
        elif deep_sky_count >= 2:
            reasons.append(tr("Più oggetti deep sky nella stessa zona"))
        elif planet_targets and not first["isBest"]:
            reasons.append(
                tr(
                    "{name} è il riferimento planetario della zona",
                    name=planet_targets[0]["name"],
                )
            )

        max_count = max(group["targetCount"] for group in ranked_groups)
        if top_group["targetCount"] == max_count and max_count > 1:
            reasons.append(tr("Maggiore concentrazione di oggetti osservabili ora"))
        elif top_group["targetCount"] > 1:
            reasons.append(tr("Più oggetti osservabili ora nella stessa zona"))
        if any(item["inPlan"] for item in targets):
            reasons.append(tr("Include una tappa del piano attualmente osservabile"))
        return reasons[:3]

    @staticmethod
    def _other_target_count_label(count: int) -> str:
        if count <= 0:
            return ""
        return (
            tr("+1 altro oggetto")
            if count == 1
            else tr("+{count} altri oggetti", count=count)
        )
