from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import NightPlanItem, SkyQuality
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
from astro_viewer.app.services.sky_compass_service import SkyCompassService


NSOM_SKY_COMPASS_ENABLED = False


@dataclass(frozen=True)
class SkyCompassNsomTarget:
    id: str
    name: str
    object_type: str
    direction: str
    display_score: int
    observable_value: float
    direction_score_contribution: float
    in_plan: bool
    is_best: bool


class SkyCompassNsomDirectionService:
    """Experimental default-off Sky Compass direction policy.

    This service preserves the public Sky Compass payload shape. It uses
    ObservableTargetValue only as the candidate base, keeps plan/best/context
    boosts as presentation policy, and exposes no NSOM fields to QML.
    """

    IN_PLAN_BONUS = 42.0
    BEST_OBJECT_BONUS = 58.0
    TARGET_PRESENCE_BONUS = 10.0

    def __init__(self, *, legacy_service: SkyCompassService | None = None) -> None:
        self._legacy_service = legacy_service or SkyCompassService()

    def compass(
        self,
        objects: list[CelestialObject],
        night_plan: list[NightPlanItem],
        best_object: CelestialObject | None,
        *,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
        has_location: bool,
        caution_text: str = "",
    ) -> dict:
        if not has_location:
            return self._legacy_service.empty("no_location", "Configura una località per usare Sky Compass.")

        plan_ids = {item.object_id for item in night_plan}
        best_id = best_object.id if best_object else ""
        targets = self._targets(objects, plan_ids, best_id, sky_quality=sky_quality, moon=moon)
        if not targets:
            return self._legacy_service.empty("no_targets", "Nessun target consigliato al momento.")

        grouped = self._group_targets(targets)
        ranked_groups = sorted(
            grouped,
            key=lambda group: (
                group["directionScore"],
                group["targetCount"],
                -SkyCompassService.DIRECTIONS.index(group["direction"]),
            ),
            reverse=True,
        )
        top = ranked_groups[0]
        alternatives = [
            {
                "direction": group["direction"],
                "targetCount": group["targetCount"],
                "targetCountLabel": self._legacy_service._target_count_label(group["targetCount"]),
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
            "targetCountLabel": self._legacy_service._available_count_label(top["targetCount"]),
            "targets": top["targets"],
            "primaryTargets": primary_targets,
            "otherTargetCount": other_target_count,
            "otherTargetCountLabel": self._legacy_service._other_target_count_label(other_target_count),
            "decisionReasons": self._legacy_service._decision_reasons(top, ranked_groups),
            "alternatives": alternatives,
            "cautionText": caution_text,
        }

    def _targets(
        self,
        objects: list[CelestialObject],
        plan_ids: set[str],
        best_id: str,
        *,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
    ) -> list[SkyCompassNsomTarget]:
        targets: list[SkyCompassNsomTarget] = []
        seen_ids = set()
        for item in objects:
            if item.id in seen_ids or not item.visible:
                continue
            direction = SkyCompassService.normalize_direction(item.direction)
            if not direction:
                continue
            observable = build_home_observable_target_value(item, sky_quality=sky_quality, moon=moon)
            in_plan = item.id in plan_ids
            is_best = item.id == best_id
            direction_score = (
                observable.value
                + (self.IN_PLAN_BONUS if in_plan else 0.0)
                + (self.BEST_OBJECT_BONUS if is_best else 0.0)
                + self.TARGET_PRESENCE_BONUS
            )
            targets.append(
                SkyCompassNsomTarget(
                    id=item.id,
                    name=item.name,
                    object_type=item.object_type,
                    direction=direction,
                    display_score=item.score,
                    observable_value=observable.value,
                    direction_score_contribution=direction_score,
                    in_plan=in_plan,
                    is_best=is_best,
                )
            )
            seen_ids.add(item.id)
        return targets

    def _group_targets(self, targets: list[SkyCompassNsomTarget]) -> list[dict]:
        grouped = {
            direction: {
                "direction": direction,
                "directionScore": 0.0,
                "targetCount": 0,
                "_targets": [],
            }
            for direction in SkyCompassService.DIRECTIONS
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
                )
            )
        for group in grouped.values():
            ranked_targets = sorted(
                group["_targets"],
                key=lambda item: (
                    item[0]["isBest"],
                    item[0]["inPlan"],
                    item[1],
                    item[0]["score"],
                ),
                reverse=True,
            )
            group["targets"] = [item[0] for item in ranked_targets]
            del group["_targets"]
        return [group for group in grouped.values() if group["targetCount"] > 0]
