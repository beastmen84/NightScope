from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.detail_nsom_comparison import (
    DETAIL_SOURCE_CATALOGUE,
    DETAIL_SOURCE_OBSERVING,
    DetailObjectNsomComparisonService,
)


def test_detail_nsom_comparison_is_strict_json_and_developer_only() -> None:
    target = _target("galaxy", "Galaxy", 88)

    comparison = _compare(target, moon=_moon(95))

    json.dumps(comparison, allow_nan=False)
    assert comparison["metadata"] == {
        "developer_only": True,
        "runtime_wiring": False,
        "runtime_object_mutated_by_comparison": False,
        "side_effects": {
            "file_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "selected_object_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "sky_compass_changed": False,
        },
    }
    assert {
        "intrinsic_target_quality",
        "observation_environment",
        "effective_observability",
        "observable_target_value",
        "observer_capability",
        "practical_target_value",
        "session_viability",
        "recommendation_confidence",
        "ownership",
    } <= set(comparison["nsom"])


def test_observing_source_detail_uses_legacy_moon_adjusted_copy_without_mutating_target() -> None:
    target = _target("galaxy", "Galaxy", 88)
    before = deepcopy(target)

    comparison = _compare(target, source=DETAIL_SOURCE_OBSERVING, moon=_moon(95))

    legacy = comparison["legacy"]["selected_object_detail"]
    assert target == before
    assert comparison["metadata"]["runtime_object_mutated_by_comparison"] is False
    assert legacy["policy"] == "observing_detail_moon_adjusted_copy"
    assert legacy["formula"] == "_object_to_qml(_moon_adjusted_object(selected_object))"
    assert legacy["display_score"] < legacy["base_score"]
    assert legacy["score_delta"] < 0
    assert legacy["display_object_replaced"] is True
    assert legacy["conditioned_copy_created"] is True
    assert legacy["components"]["moon_penalty"] > 0
    assert "sky_background_component:not_part_of_selected_object_detail" in legacy["unavailable_components"]
    assert comparison["nsom"]["observation_environment"]["lunar_sky_background"] < 1.0
    assert comparison["nsom"]["ownership"]["sky_effects"]["legacy_detail_uses_moon_adjustment"] is True


def test_catalogue_source_detail_keeps_raw_legacy_score_while_nsom_reports_sky_context() -> None:
    target = _target("catalogue-galaxy", "Galaxy", 88, visibility_class="Catalogo Messier")

    comparison = _compare(target, source=DETAIL_SOURCE_CATALOGUE, moon=_moon(95))

    legacy = comparison["legacy"]["selected_object_detail"]
    assert legacy["policy"] == "catalogue_detail_raw_object"
    assert legacy["formula"] == "_object_to_qml(selected_object)"
    assert legacy["display_score"] == legacy["base_score"] == 88
    assert legacy["score_delta"] == 0
    assert legacy["display_object_replaced"] is False
    assert legacy["conditioned_copy_created"] is False
    assert legacy["components"]["moon_adjustment"] == "not_applied_to_catalogue_detail"
    assert "moon_condition_breakdown:not_available_for_catalogue_detail" in legacy["unavailable_components"]
    assert comparison["nsom"]["observation_environment"]["lunar_sky_background"] < 1.0
    assert comparison["nsom"]["ownership"]["sky_effects"]["legacy_detail_uses_moon_adjustment"] is False


def test_session_viability_is_metadata_and_does_not_change_detail_target_values() -> None:
    target = _target("galaxy", "Galaxy", 88)
    good = _compare(target, weather=_weather(90), moon=_moon(15))
    blocked = _compare(
        target,
        weather=_weather(10, cloud_cover=96, precipitation_probability=85),
        moon=_moon(15),
    )

    assert _observable(blocked) == pytest.approx(_observable(good))
    assert _practical(blocked) == pytest.approx(_practical(good))
    assert _legacy_display(blocked) == pytest.approx(_legacy_display(good))

    session = blocked["nsom"]["session_viability"]
    assert session["state"] == "blocked"
    assert session["value"] == pytest.approx(0.0)
    assert session["score_effect_on_observable_target_value"] == pytest.approx(0.0)
    assert session["score_effect_on_practical_target_value"] == pytest.approx(0.0)
    ownership = blocked["nsom"]["ownership"]["session_weather_effects"]
    assert ownership["used_in_observable_target_value"] is False
    assert ownership["used_in_practical_target_value"] is False
    assert ownership["legacy_detail_uses_session_weather"] is False


def test_equipment_changes_practical_value_only_for_detail_comparison() -> None:
    target = _target("galaxy", "Galaxy", 88)
    small = _compare(
        target,
        telescope=_telescope(name="Small Manual", aperture_mm=60, focal_length_mm=400, mount="manual"),
        moon=_moon(15),
    )
    large = _compare(
        target,
        telescope=_telescope(name="Large GoTo", aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
        moon=_moon(15),
    )

    assert _observable(large) == pytest.approx(_observable(small))
    assert _practical(large) > _practical(small)
    assert _legacy_display(large) == pytest.approx(_legacy_display(small))
    ownership = large["nsom"]["ownership"]["observer_equipment_effects"]
    assert ownership["used_in_observable_target_value"] is False
    assert ownership["used_in_practical_target_value"] is True
    assert ownership["legacy_detail_score_uses_equipment"] is False


def test_confidence_is_metadata_only_for_detail_comparison() -> None:
    target = _target("galaxy", "Galaxy", 88)
    low = _compare(
        target,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
        moon=_moon(15),
    )
    high = _compare(
        target,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
        moon=_moon(15),
    )

    assert low["nsom"]["recommendation_confidence"]["value"] < high["nsom"]["recommendation_confidence"]["value"]
    assert low["nsom"]["recommendation_confidence"]["score_factor"] is False
    assert low["nsom"]["recommendation_confidence"]["score_effect"] == pytest.approx(0.0)
    assert _observable(low) == pytest.approx(_observable(high))
    assert _practical(low) == pytest.approx(_practical(high))
    assert _legacy_display(low) == pytest.approx(_legacy_display(high))


def test_detail_nsom_comparison_is_not_wired_into_runtime_or_qml() -> None:
    app_controller = (Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).parents[1] / "app" / "ui").rglob("*.qml")
    )

    assert "DetailObjectNsomComparisonService" not in app_controller
    assert "detail_nsom_comparison" not in app_controller
    assert "DetailObjectNsomComparisonService" not in qml_text
    assert "detail_nsom_comparison" not in qml_text


def _compare(
    target: CelestialObject,
    *,
    source: str = DETAIL_SOURCE_OBSERVING,
    weather: WeatherSummary | None = None,
    sky_quality: SkyQuality | None = None,
    telescope: Telescope | None = None,
    moon: MoonSummary | None = None,
    confidence: RecommendationConfidence | None = None,
) -> dict[str, object]:
    return DetailObjectNsomComparisonService().compare(
        target,
        source=source,
        weather=weather or _weather(90),
        sky_quality=sky_quality or _sky_quality(3),
        telescope=telescope or _telescope(),
        moon=moon or _moon(15),
        confidence=confidence,
    )


def _observable(comparison: dict[str, object]) -> float:
    return float(comparison["nsom"]["observable_target_value"]["value"])


def _practical(comparison: dict[str, object]) -> float:
    return float(comparison["nsom"]["practical_target_value"]["value"])


def _legacy_display(comparison: dict[str, object]) -> float:
    return float(comparison["legacy"]["selected_object_detail"]["display_score"])


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    visibility_class: str = "",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.replace("_", " ").title(),
        object_type=object_type,
        image="",
        magnitude="8.0",
        distance="",
        max_altitude="55 gradi",
        direction="Sud",
        best_time="22:30",
        observing_window="21:00 - 02:00",
        notes="Deterministic Detail NSOM fixture.",
        recommended_setup="Telescopio",
        visibility_class=visibility_class,
        azimuth="180 gradi",
        time_above_horizon="4 h",
        visible=True,
        score=score,
        score_label="Buono",
        difficulty="Media",
        recommended_setup_type="Telescope",
        apparent_size="20 arcmin",
    )


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Buono",
        score_value=score,
        explanation="Deterministic Detail NSOM weather fixture.",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=8,
        humidity=55,
        temperature_c=12.0,
        alert="",
    )


def _sky_quality(bortle: int) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=6.2,
        sky_brightness=21.2,
        source="deterministic_fixture",
        description="Deterministic Detail NSOM sky fixture.",
        confidence="high",
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture Moon.",
        image="",
        phase_angle=90.0,
    )


def _telescope(
    *,
    name: str = "Medium GoTo",
    aperture_mm: int = 130,
    focal_length_mm: int = 900,
    mount: str = "GoTo EQ",
) -> Telescope:
    return Telescope(
        id=name.casefold().replace(" ", "-"),
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Reflector",
        mount=mount,
    )
