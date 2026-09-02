from __future__ import annotations

from statistics import mean

from astro_viewer.app.models.condition_inputs import ObservationConditionInputs
from astro_viewer.app.models.nsom import NsomTargetClass
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import ObservingCategoryScores
from astro_viewer.app.services.nsom_observation_environment import (
    NsomObservationEnvironmentService,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.localization import tr


class NsomCategoryScoreService:
    """Projects broad Home category conditions through the canonical Sky layer."""

    _DEEP_SKY_CLASSES = (
        NsomTargetClass.GALAXY,
        NsomTargetClass.DIFFUSE_NEBULA,
        NsomTargetClass.OPEN_CLUSTER,
        NsomTargetClass.GLOBULAR_CLUSTER,
    )

    def __init__(self) -> None:
        self._environment_service = NsomObservationEnvironmentService()

    def scores(self, inputs: ObservationConditionInputs) -> ObservingCategoryScores:
        planetary_score = self._score_for_class(NsomTargetClass.PLANET, inputs)
        deep_sky_score = round(
            mean(self._score_for_class(target_class, inputs) for target_class in self._DEEP_SKY_CLASSES)
        )
        scorer = ObservingScoreService()
        return ObservingCategoryScores(
            planetary_score=planetary_score,
            deep_sky_score=deep_sky_score,
            planetary_label=scorer.score_label(planetary_score),
            deep_sky_label=scorer.score_label(deep_sky_score),
            explanation=tr(
                "Condizioni di categoria NSOM: ambiente atmosferico, fondo cielo e Luna "
                "sono applicati una sola volta; sessione ed equipaggiamento restano separati."
            ),
        )

    def _score_for_class(
        self,
        target_class: NsomTargetClass,
        inputs: ObservationConditionInputs,
    ) -> int:
        observable = self._environment_service.observable_target_value(
            _reference_target(target_class),
            inputs,
        )
        return max(0, min(100, round(observable.value)))


def _reference_target(target_class: NsomTargetClass) -> CelestialObject:
    return CelestialObject(
        id=f"category-{target_class.value}",
        name=f"Category {target_class.value}",
        object_type=_object_type_for_target_class(target_class),
        image="",
        magnitude="n/d",
        distance="",
        max_altitude="45°",
        direction="Sud",
        best_time="21:00",
        observing_window="21:00 - 02:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="180°",
        time_above_horizon="3 h",
        visible=True,
        score=100,
        intrinsic_score=100,
        difficulty="Media",
    )


def _object_type_for_target_class(target_class: NsomTargetClass) -> str:
    return {
        NsomTargetClass.PLANET: "Pianeta",
        NsomTargetClass.GALAXY: "Galaxy",
        NsomTargetClass.DIFFUSE_NEBULA: "Diffuse nebula",
        NsomTargetClass.OPEN_CLUSTER: "Open cluster",
        NsomTargetClass.GLOBULAR_CLUSTER: "Globular cluster",
    }[target_class]
