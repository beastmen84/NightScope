from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import date
from typing import Any

from astro_viewer.app.models.nsom import (
    ObservableTargetValue,
    ObservationOpportunity,
    ObserverCapability,
    PracticalTargetValue,
    RecommendationConfidence,
    SessionViability,
)


def build_observer_capability_profile_from_recommendation(recommendation: Any) -> ObserverCapability:
    """Translate an existing recommendation output into observer capability."""

    setup_type = _text_field(recommendation, "setupType", "recommended_setup_type", "equipmentType")
    setup_text = _text_field(recommendation, "setupText", "recommended_setup", "setup")
    telescope_name = _text_field(recommendation, "telescopeName")
    setup_options = _value(recommendation, "setupOptions", "setup_options", default=()) or ()
    normalized = f"{setup_type} {setup_text} {telescope_name}".lower()
    notes = tuple(
        item
        for item in (
            f"setup_type={setup_type}" if setup_type else "",
            f"telescope={telescope_name}" if telescope_name else "",
        )
        if item
    )

    if "occhio" in normalized or "naked" in normalized:
        return ObserverCapability(
            light_grasp=0.1,
            resolution=0.1,
            field_of_view=1.0,
            magnification_range=0.05,
            tracking_or_goto=0.0,
            practical_comfort=0.9,
            notes=notes,
        )
    if "binoc" in normalized or "binocular" in normalized:
        return ObserverCapability(
            light_grasp=0.35,
            resolution=0.3,
            field_of_view=0.95,
            magnification_range=0.2,
            tracking_or_goto=0.1,
            practical_comfort=0.85,
            notes=notes,
        )
    if "smart" in normalized or "eaa" in normalized:
        return ObserverCapability(
            light_grasp=0.75,
            resolution=0.7,
            field_of_view=0.55,
            magnification_range=0.65,
            tracking_or_goto=0.9,
            automation_or_eaa=0.9,
            practical_comfort=0.85,
            observing_style="assisted",
            notes=notes,
        )

    profile = ObserverCapability(
        light_grasp=0.85 if ("telesc" in normalized or telescope_name) else 0.5,
        resolution=0.8 if ("telesc" in normalized or telescope_name) else 0.5,
        field_of_view=0.45 if ("telesc" in normalized or telescope_name) else 0.5,
        magnification_range=0.8 if ("telesc" in normalized or telescope_name) else 0.5,
        tracking_or_goto=0.6 if telescope_name else 0.4,
        practical_comfort=0.7,
        notes=notes,
    )
    return _profile_with_option_context(profile, setup_options)


def build_practical_target_value(
    observable_target_value: ObservableTargetValue,
    observer_capability: ObserverCapability,
    *,
    capability_summary: float | None = None,
) -> PracticalTargetValue:
    """Build observer-specific NSOM value without mutating the observable target."""

    return PracticalTargetValue.from_observable(
        observable_target_value=observable_target_value,
        observer_capability=observer_capability,
        capability_summary=capability_summary,
    )


def build_recommendation_confidence(
    *,
    weather_summary: Any | None = None,
    aod_result: Any | None = None,
    local_atmosphere: Any | None = None,
    viirs_available: bool | None = None,
    moon_geometry_available: bool | None = None,
    provider_fallback_used: bool | None = None,
    today: date | None = None,
    notes: tuple[str, ...] = (),
) -> RecommendationConfidence:
    """Build parallel NSOM recommendation confidence from existing runtime data."""

    return RecommendationConfidence(
        weather_confidence=_weather_confidence(weather_summary),
        aod_confidence=_aod_confidence(aod_result, today=today),
        openaq_confidence=_openaq_confidence(local_atmosphere),
        viirs_confidence=_boolean_confidence(viirs_available),
        moon_geometry_confidence=_boolean_confidence(moon_geometry_available),
        provider_fallback_confidence=0.6 if provider_fallback_used else None,
        notes=tuple(notes),
    )


def build_session_viability(
    *,
    weather_summary: Any | None = None,
    blocking_status: Any | None = None,
    value: float | None = None,
) -> SessionViability:
    """Build session-owned viability metadata without changing target values."""

    if blocking_status is None:
        blocks_plan = bool(
            _numeric_field(weather_summary, "precipitation_probability", default=0.0) >= 65.0
            or _numeric_field(weather_summary, "cloud_cover", default=0.0) >= 85.0
            or _numeric_field(weather_summary, "score_value", default=100.0) <= 25.0
        )
    else:
        blocks_plan = bool(_value(blocking_status, "blocks_plan", "blocksPlan", default=False))
    weather_suitability = 0.0 if blocks_plan else 1.0
    state = "blocked" if blocks_plan else "usable"
    reason = _text_field(blocking_status, "reason", "detail")
    return SessionViability.from_components(
        value=value,
        weather_suitability=weather_suitability,
        blocking_factor=0.0 if blocks_plan else 1.0,
        state=state,
        reason=reason,
        notes=("nsom:runtime_session", "session:binary_usability"),
    )


def build_observation_opportunity(
    practical_target_value: PracticalTargetValue,
    *,
    observing_window_quality: float = 1.0,
    chronology_fit: float = 1.0,
    session_viability: float | None = None,
    session: SessionViability | None = None,
    practical_constraints: float = 1.0,
    confidence: RecommendationConfidence | None = None,
    context: tuple[str, ...] = (),
) -> ObservationOpportunity:
    """Build an NSOM opportunity without changing upstream DTOs."""

    session_context = _session_from_inputs(session_viability=session_viability, session=session)
    return ObservationOpportunity(
        practical_target_value=practical_target_value,
        observing_window_quality=observing_window_quality,
        chronology_fit=chronology_fit,
        session=session_context,
        practical_constraints=practical_constraints,
        confidence=confidence,
        context=tuple(context),
    )


def _profile_with_option_context(
    profile: ObserverCapability,
    setup_options: Any,
) -> ObserverCapability:
    option_text = " ".join(
        str(_mapping_or_attr(option, "role", default=""))
        + " "
        + str(_mapping_or_attr(option, "displayLabel", default=""))
        for option in setup_options
        if isinstance(option, Mapping) or hasattr(option, "role")
    ).lower()
    field_of_view = profile.field_of_view
    magnification_range = profile.magnification_range
    if "campo largo" in option_text or "wide" in option_text:
        field_of_view = max(field_of_view, 0.75)
    if "alto ingrandimento" in option_text or "high" in option_text:
        magnification_range = max(magnification_range, 0.75)
    return ObserverCapability(
        light_grasp=profile.light_grasp,
        resolution=profile.resolution,
        field_of_view=field_of_view,
        magnification_range=magnification_range,
        tracking_or_goto=profile.tracking_or_goto,
        automation_or_eaa=profile.automation_or_eaa,
        filters=profile.filters,
        experience_level=profile.experience_level,
        observing_style=profile.observing_style,
        practical_comfort=profile.practical_comfort,
        notes=profile.notes,
    )


def _session_from_inputs(
    *,
    session_viability: float | None,
    session: SessionViability | None,
) -> SessionViability:
    if session is None:
        return SessionViability.from_components(
            value=1.0 if session_viability is None else session_viability,
        )
    if session_viability is None:
        return session

    requested_session = SessionViability.from_components(value=session_viability)
    if not math.isclose(requested_session.value, session.value, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("session_viability conflicts with session.value")
    return session


def _weather_confidence(weather_summary: Any | None) -> float | None:
    if weather_summary is None:
        return None
    return 1.0 if _value(weather_summary, "score_value", "scoreValue") is not None else None


def _aod_confidence(aod_result: Any | None, *, today: date | None) -> float | None:
    if aod_result is None or not bool(_value(aod_result, "available", default=False)):
        return None
    category = _text_field(aod_result, "freshness_category")
    if category:
        return _aod_confidence_from_category(category)
    age_days = _age_days_from_iso_date(_text_field(aod_result, "acquisition_date"), today=today)
    if age_days is None:
        return 0.5
    if age_days <= 3.0:
        return 1.0
    if age_days <= 7.0:
        return 0.5
    return 0.0


def _openaq_confidence(local_atmosphere: Any | None) -> float | None:
    if local_atmosphere is None or not bool(_value(local_atmosphere, "has_data", default=False)):
        return None
    return {
        "current": 1.0,
        "recent": 0.7,
        "stale": 0.3,
        "historical": 0.0,
    }.get(_text_field(local_atmosphere, "freshness_category").lower(), 0.0)


def _aod_confidence_from_category(category: str) -> float:
    return {
        "current": 1.0,
        "recent": 1.0,
        "stale": 0.5,
        "historical": 0.0,
    }.get(category.strip().lower(), 0.0)


def _boolean_confidence(value: bool | None) -> float | None:
    if value is None:
        return None
    return 1.0 if value else 0.0


def _age_days_from_iso_date(value: str, *, today: date | None) -> float | None:
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value[:10])
    except ValueError:
        return None
    reference = today or date.today()
    return float(max(0, (reference - parsed).days))


def _numeric_field(item: Any, *names: str, default: float) -> float:
    value = _value(item, *names, default=default)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _text_field(item: Any, *names: str) -> str:
    value = _value(item, *names, default="")
    return "" if value is None else str(value)


def _value(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        value = _mapping_or_attr(item, name, default=None)
        if value is not None:
            return value
    return default


def _mapping_or_attr(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)
