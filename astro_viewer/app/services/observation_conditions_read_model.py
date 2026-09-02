"""Preserve raw targets beside condition-adjusted presentation projections."""

from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.observation_conditions_service import (
    ConditionedTarget,
    TargetConditionBreakdown,
)


@dataclass(frozen=True)
class ObservationConditionedTargetReadModel:
    """Internal boundary between raw target input and conditioned display data."""

    object_id: str
    name: str
    source: str
    raw_target: CelestialObject
    display_target: CelestialObject
    condition_breakdown: TargetConditionBreakdown
    raw_score: int
    display_score: int
    display_notes: str
    condition_flags: tuple[str, ...]
    nsom_input_policy: str = "raw_target_score"

    @property
    def nsom_target_input(self) -> CelestialObject:
        """Universe-owned NSOM target input, before display-only conditioning."""

        return self.raw_target

    @property
    def qml_display_target(self) -> CelestialObject:
        """Compatibility display object for existing QML payloads."""

        return self.display_target

    @property
    def applied_components(self) -> tuple[str, ...]:
        return self.condition_breakdown.applied_components

    def to_dict(self) -> dict[str, object]:
        return nsom_to_json_compatible(
            {
                "object_id": self.object_id,
                "name": self.name,
                "source": self.source,
                "raw_score": self.raw_score,
                "display_score": self.display_score,
                "display_notes": self.display_notes,
                "condition_flags": self.condition_flags,
                "applied_components": self.applied_components,
                "nsom_input_policy": self.nsom_input_policy,
                "condition_breakdown": self.condition_breakdown,
                "raw_target": self.raw_target,
                "display_target": self.display_target,
            }
        )


class ObservationConditionsReadModelBuilder:
    """Builds ObservationConditions read models without changing runtime DTOs."""

    def from_conditioned_target(
        self,
        conditioned: ConditionedTarget,
        *,
        source: str,
        raw_target_override: CelestialObject | None = None,
    ) -> ObservationConditionedTargetReadModel:
        raw_target = raw_target_override or conditioned.original_target or conditioned.target
        display_target = conditioned.target
        return ObservationConditionedTargetReadModel(
            object_id=display_target.id,
            name=display_target.name,
            source=source,
            raw_target=raw_target,
            display_target=display_target,
            condition_breakdown=conditioned.breakdown,
            raw_score=raw_target.score,
            display_score=display_target.score,
            display_notes=display_target.notes,
            condition_flags=tuple(display_target.condition_flags),
        )

    def from_conditioned_targets(
        self,
        conditioned_targets: tuple[ConditionedTarget, ...] | list[ConditionedTarget],
        *,
        source: str,
        raw_targets_by_id: dict[str, CelestialObject] | None = None,
    ) -> tuple[ObservationConditionedTargetReadModel, ...]:
        raw_targets = raw_targets_by_id or {}
        return tuple(
            self.from_conditioned_target(
                conditioned,
                source=source,
                raw_target_override=raw_targets.get(conditioned.target.id),
            )
            for conditioned in conditioned_targets
        )

    def from_display_targets(
        self,
        display_targets: tuple[CelestialObject, ...] | list[CelestialObject],
        *,
        source: str,
        raw_targets_by_id: dict[str, CelestialObject] | None = None,
    ) -> tuple[ObservationConditionedTargetReadModel, ...]:
        raw_targets = raw_targets_by_id or {}
        return tuple(
            self.from_conditioned_target(
                ConditionedTarget(
                    target=display_target,
                    original_target=raw_targets.get(display_target.id, display_target),
                    breakdown=_display_only_breakdown(
                        raw_targets.get(display_target.id, display_target),
                        display_target,
                    ),
                ),
                source=source,
            )
            for display_target in display_targets
        )


def _display_only_breakdown(
    raw_target: CelestialObject,
    display_target: CelestialObject,
) -> TargetConditionBreakdown:
    display_delta = max(0.0, float(raw_target.score - display_target.score))
    return TargetConditionBreakdown(
        object_id=display_target.id,
        base_score=raw_target.score,
        adjusted_score=display_target.score,
        pollution_penalty=display_delta if "light_pollution" in display_target.condition_flags else 0.0,
        applied_components=tuple(display_target.condition_flags),
        diagnostic_notes=(
            "read_model:display_only_projection",
            "read_model:raw_target_preserved_for_nsom_input",
        ),
        already_adjusted_flags=tuple(display_target.condition_flags),
    )
