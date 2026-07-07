from __future__ import annotations

import math

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.sky import AdvancedObservingScores

ADVANCED_OBSERVING_NSOM_PRESENTATION_SCHEMA_VERSION = "advanced_observing_nsom_presentation_v1"


def build_advanced_observing_nsom_presentation(
    nsom_scores: AdvancedObservingScores | None,
    legacy_scores: AdvancedObservingScores | None,
    *,
    session_state: str = "",
    confidence_value: float | None = None,
    runtime_state: str = "default_on_internal_projection",
) -> dict[str, object]:
    """Project internal Advanced Observing NSOM scores into the agreed contract.

    The projection is intentionally internal. It does not replace the public
    `advancedScores` payload and it is not a Planner or notification input.
    """

    payload = {
        "schemaVersion": ADVANCED_OBSERVING_NSOM_PRESENTATION_SCHEMA_VERSION,
        "runtimeState": runtime_state if nsom_scores else "disabled",
        "enabled": nsom_scores is not None,
        "currentQmlProperty": "advancedScores",
        "futureQmlProperty": "advancedObservingNsom",
        "summary": {
            "title": "Advanced Observing NSOM",
            "status": (
                runtime_state
                if nsom_scores
                else "disabled_internal_projection"
            ),
            "displayPolicy": "separate_from_legacy_advanced_scores",
            "scoreSemantics": (
                "Category diagnostics from NSOM ObservableTargetValue; not an "
                "actionability score, Planner input or notification threshold."
            ),
        },
        "categories": _categories(nsom_scores, legacy_scores),
        "session": {
            "included": True,
            "placement": "metadata_outside_category_value",
            "scoreEffect": 0.0,
            "state": session_state,
            "semantics": "actionability and caution text only",
        },
        "confidence": {
            "included": True,
            "placement": "metadata_outside_category_value",
            "scoreEffect": 0.0,
            "value": _finite_or_none(confidence_value),
            "semantics": "source trust only",
        },
        "consumerPolicy": {
            "replacesAdvancedScores": False,
            "plannerInput": False,
            "notificationInput": False,
            "homeBestObjectInput": False,
            "skyCompassInput": False,
        },
        "runtimeSafety": {
            "defaultOff": False,
            "noRuntimeFileWrites": True,
            "noAutomaticLogging": True,
            "noNetwork": True,
            "noMutationOfRuntimeObjects": True,
        },
    }
    return nsom_to_json_compatible(payload)


def _categories(
    nsom_scores: AdvancedObservingScores | None,
    legacy_scores: AdvancedObservingScores | None,
) -> tuple[dict[str, object], ...]:
    if nsom_scores is None:
        return ()

    return (
        _category_payload(
            "planetary",
            "Planetary conditions",
            nsom_scores.planetary_score,
            _legacy_value(legacy_scores, "planetary_score", nsom_scores.planetary_score),
            nsom_scores.planetary_label,
            _legacy_label(legacy_scores, "planetary_label", nsom_scores.planetary_label),
            included_sky_components=(
                "geometric_visibility",
                "horizon_context",
                "atmospheric_transparency_from_seeing",
                "planetary_moon_background_protected",
                "planetary_static_sky_background_protected",
            ),
        ),
        _category_payload(
            "deepSky",
            "Deep-sky conditions",
            nsom_scores.deep_sky_score,
            _legacy_value(legacy_scores, "deep_sky_score", nsom_scores.deep_sky_score),
            nsom_scores.deep_sky_label,
            _legacy_label(legacy_scores, "deep_sky_label", nsom_scores.deep_sky_label),
            included_sky_components=(
                "geometric_visibility",
                "horizon_context",
                "atmospheric_transparency_from_transparency",
                "lunar_sky_background",
                "static_sky_background",
            ),
        ),
    )


def _category_payload(
    category_id: str,
    title: str,
    diagnostic_value: float | int | None,
    legacy_value: float | int | None,
    label: str,
    legacy_label: str,
    *,
    included_sky_components: tuple[str, ...],
) -> dict[str, object]:
    return {
        "id": category_id,
        "title": title,
        "diagnosticValue": _finite_or_none(diagnostic_value),
        "diagnosticLabel": label,
        "legacyCompatibilityValue": _finite_or_none(legacy_value),
        "legacyCompatibilityLabel": legacy_label,
        "scoreMeaning": "NSOM ObservableTargetValue category diagnostic",
        "scoreRange": "0..100",
        "mathPipeline": (
            "IntrinsicTargetQuality",
            "ObservationEnvironment",
            "EffectiveObservability",
            "ObservableTargetValue",
        ),
        "includedSkyComponents": included_sky_components,
        "excludedFromCategoryValue": (
            "ObserverCapability",
            "PracticalTargetValue",
            "SessionViability",
            "RecommendationConfidence",
            "ObservationOpportunity",
        ),
        "positiveFactors": (),
        "limitingFactors": (),
    }


def _legacy_value(
    scores: AdvancedObservingScores | None,
    attr: str,
    fallback: float | int | None,
) -> float | int | None:
    if scores is None:
        return fallback
    return getattr(scores, attr)


def _legacy_label(
    scores: AdvancedObservingScores | None,
    attr: str,
    fallback: str,
) -> str:
    if scores is None:
        return fallback
    return str(getattr(scores, attr))


def _finite_or_none(value: object) -> object:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return value
