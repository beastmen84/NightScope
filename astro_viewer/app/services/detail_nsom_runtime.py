from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    IntrinsicTargetQuality,
    ObservableTargetValue,
    ObservationEnvironment,
    PracticalTargetValue,
    RecommendationConfidence,
    SessionViability,
    nsom_to_json_compatible,
    observer_capability_weight_profile_for_target,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.home_nsom_observable import build_home_observation_environment
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_intrinsic_target_quality,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.observer_capability_adapter import build_observer_capability_for_target


NSOM_DETAIL_OBJECT_ENABLED = False

DETAIL_SOURCE_OBSERVING = "observing"
DETAIL_SOURCE_CATALOGUE = "catalogue"


@dataclass(frozen=True)
class DetailObjectNsomPayload:
    """Internal Detail/Object NSOM payload.

    This DTO is deliberately not a QML property. It preserves the existing
    `selectedObject` contract and carries NSOM values in a separate internal
    structure for the future Detail/Object migration steps.
    """

    object_id: str
    name: str
    object_type: str
    source: str
    intrinsic_target_quality: IntrinsicTargetQuality
    observation_environment: ObservationEnvironment
    effective_observability: EffectiveObservability
    observable_target_value: ObservableTargetValue
    practical_target_value: PracticalTargetValue
    session_viability: SessionViability
    recommendation_confidence: RecommendationConfidence
    blocking_status: WeatherBlockingStatus
    selected_object_policy: dict[str, object]
    runtime_object_mutated: bool

    def to_dict(self) -> dict[str, object]:
        observer = self.practical_target_value.observer_capability
        return nsom_to_json_compatible(
            {
                "schemaVersion": "detail-object-nsom-runtime-v1",
                "objectId": self.object_id,
                "name": self.name,
                "objectType": self.object_type,
                "source": self.source,
                "targetClass": self.observable_target_value.target_class,
                "intrinsicTargetQuality": self.intrinsic_target_quality,
                "observationEnvironment": self.observation_environment,
                "effectiveObservability": self.effective_observability,
                "observableTargetValue": self.observable_target_value,
                "observerCapability": {
                    **nsom_to_json_compatible(observer),
                    "summaryForPlanning": observer.summary_for_planning(),
                    "qTarget": self.practical_target_value.observer_capability_summary,
                    "targetClassWeightingProfile": observer_capability_weight_profile_for_target(
                        self.observable_target_value.target_class
                    ),
                },
                "practicalTargetValue": self.practical_target_value,
                "sessionViability": {
                    **nsom_to_json_compatible(self.session_viability),
                    "role": "metadata_only_for_detail_object",
                    "scoreFactor": False,
                    "scoreEffectOnObservableTargetValue": 0.0,
                    "scoreEffectOnPracticalTargetValue": 0.0,
                    "blockingStatus": self.blocking_status,
                },
                "recommendationConfidence": {
                    **nsom_to_json_compatible(self.recommendation_confidence),
                    "value": self.recommendation_confidence.value,
                    "role": "metadata_only",
                    "scoreFactor": False,
                    "scoreEffect": 0.0,
                },
                "selectedObjectPolicy": self.selected_object_policy,
                "ownership": {
                    "observableTargetValue": (
                        "Universe target quality multiplied by Sky observation environment."
                    ),
                    "practicalTargetValue": (
                        "Observer capability projection applied after ObservableTargetValue."
                    ),
                    "sessionViability": "Session metadata only for Detail/Object.",
                    "recommendationConfidence": "Confidence metadata only; never a score modifier.",
                    "observationOpportunity": "not_used_for_detail_object",
                },
                "metadata": {
                    "internalOnly": True,
                    "runtimePath": True,
                    "defaultFlagEnabled": NSOM_DETAIL_OBJECT_ENABLED,
                    "qmlExposure": False,
                    "selectedObjectPayloadChanged": False,
                    "selectedObjectFieldsAdded": False,
                    "runtimeObjectMutated": self.runtime_object_mutated,
                    "fileWrites": False,
                    "automaticLogging": False,
                    "network": False,
                    "homeChanged": False,
                    "bestObjectChanged": False,
                    "plannerChanged": False,
                    "skyCompassChanged": False,
                },
            }
        )


class DetailObjectNsomRuntimeService:
    """Builds the default-off internal NSOM payload for selected-object Detail."""

    def payload(
        self,
        item: CelestialObject,
        *,
        source: str,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
        confidence: RecommendationConfidence | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
    ) -> DetailObjectNsomPayload:
        before = deepcopy(item)
        source_name = _normalize_source(source)
        blocking = blocking_status or NightPlannerService.weather_blocking_status(weather)
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:detail_object_runtime", "confidence:metadata_only"),
        )
        intrinsic = build_intrinsic_target_quality(item)
        environment = build_home_observation_environment(
            item,
            intrinsic,
            sky_quality=sky_quality,
            moon=moon,
        )
        effective = EffectiveObservability.from_environment(environment)
        observable = ObservableTargetValue.from_intrinsic(
            intrinsic_target_quality=intrinsic,
            effective_observability=effective,
            target_class=intrinsic.target_class,
        )
        observer = build_observer_capability_for_target(
            item,
            telescope=telescope,
            context_note="nsom:detail_object_runtime_observer_capability",
        )
        q_target = project_observer_capability_for_target(observer, observable.target_class)
        practical = build_practical_target_value(
            observable,
            observer,
            capability_summary=q_target,
        )
        session = build_session_viability(weather_summary=weather, blocking_status=blocking)

        return DetailObjectNsomPayload(
            object_id=item.id,
            name=item.name,
            object_type=item.object_type,
            source=source_name,
            intrinsic_target_quality=intrinsic,
            observation_environment=environment,
            effective_observability=effective,
            observable_target_value=observable,
            practical_target_value=practical,
            session_viability=session,
            recommendation_confidence=recommendation_confidence,
            blocking_status=blocking,
            selected_object_policy=_selected_object_policy(source_name),
            runtime_object_mutated=item != before,
        )


def _normalize_source(source: str) -> str:
    normalized = source.strip().casefold()
    if normalized == DETAIL_SOURCE_CATALOGUE:
        return DETAIL_SOURCE_CATALOGUE
    return DETAIL_SOURCE_OBSERVING


def _selected_object_policy(source: str) -> dict[str, object]:
    if source == DETAIL_SOURCE_CATALOGUE:
        return {
            "currentQmlProperty": "selectedObject",
            "selectedObjectPreserved": True,
            "nsomFieldsAddedToSelectedObject": False,
            "internalPayloadName": "detailObjectNsom",
            "visibleQmlExposureApproved": False,
            "legacyDisplayPolicy": "catalogue_detail_raw_object",
            "selectedObjectFormula": "_object_to_qml(selected_object)",
            "selectedObjectScoreMeaning": "raw catalogue compatibility score",
            "nsomPayloadRole": "parallel internal Detail/Object target context",
        }
    return {
        "currentQmlProperty": "selectedObject",
        "selectedObjectPreserved": True,
        "nsomFieldsAddedToSelectedObject": False,
        "internalPayloadName": "detailObjectNsom",
        "visibleQmlExposureApproved": False,
        "legacyDisplayPolicy": "observing_detail_moon_adjusted_copy",
        "selectedObjectFormula": "_object_to_qml(_moon_adjusted_object(selected_object))",
        "selectedObjectScoreMeaning": "moon-adjusted compatibility display score",
        "nsomPayloadRole": "parallel internal Detail/Object target context",
    }
