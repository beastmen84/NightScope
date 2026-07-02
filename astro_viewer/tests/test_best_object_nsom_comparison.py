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
from astro_viewer.app.services.best_object_nsom_comparison import BestObjectNsomComparisonService
from astro_viewer.app.services.observing_score_service import ObservingScoreService


def test_best_object_nsom_comparison_good_session_is_strict_json_and_developer_only() -> None:
    targets = [_target("planet", "Pianeta", 86, difficulty="Facile"), _target("galaxy", "Galaxy", 90)]

    comparison = _compare(targets, weather=_weather(90), sky_quality=_sky_quality(3), moon=_moon(10))

    json.dumps(comparison, allow_nan=False)
    assert comparison["metadata"]["developer_only"] is True
    assert comparison["metadata"]["runtime_wiring"] is False
    assert comparison["metadata"]["side_effects"] == {
        "file_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "best_object_changed": False,
        "recommended_deep_sky_changed": False,
        "planner_changed": False,
        "sky_compass_changed": False,
    }
    assert comparison["legacy_formula"]["formula"] == "item.score * weather_factor * difficulty_factor"
    assert comparison["legacy_formula"]["selected_object_id"] == ObservingScoreService().best_object(
        targets,
        _weather(90),
    ).id

    galaxy = _entry(comparison, "galaxy")
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
    } <= set(galaxy["nsom"])
    assert "intrinsic_target_quality:not_exposed_separately" in galaxy["legacy"]["best_object"][
        "unavailable_components"
    ]


def test_poor_weather_changes_legacy_best_object_but_not_nsom_target_values() -> None:
    target = _target("galaxy", "Galaxy", 90)
    good = _compare([target], weather=_weather(90), sky_quality=_sky_quality(3), moon=_moon(10))
    poor = _compare([target], weather=_weather(35), sky_quality=_sky_quality(3), moon=_moon(10))

    assert _legacy_best(poor, "galaxy") < _legacy_best(good, "galaxy")
    assert _observable(poor, "galaxy") == pytest.approx(_observable(good, "galaxy"))
    assert _practical(poor, "galaxy") == pytest.approx(_practical(good, "galaxy"))

    legacy = _entry(poor, "galaxy")["legacy"]["best_object"]
    assert legacy["components"]["weather_factor"] == pytest.approx(0.35)
    assert legacy["ownership_mixing"]["weather_session"]["mixed_into_final_score"] is True
    session = _session(poor, "galaxy")
    assert session["weather_suitability"] == pytest.approx(0.35)
    assert session["score_effect_on_observable_target_value"] == pytest.approx(0.0)
    assert session["score_effect_on_practical_target_value"] == pytest.approx(0.0)


def test_blocked_session_is_metadata_and_legacy_formula_still_uses_weather_floor() -> None:
    target = _target("galaxy", "Galaxy", 90)
    good = _compare([target], weather=_weather(90), sky_quality=_sky_quality(3), moon=_moon(10))
    blocked = _compare(
        [target],
        weather=_weather(10, cloud_cover=95, precipitation_probability=80),
        sky_quality=_sky_quality(3),
        moon=_moon(10),
    )

    assert _legacy_best(blocked, "galaxy") == pytest.approx(90 * 0.25 * 0.94)
    assert _observable(blocked, "galaxy") == pytest.approx(_observable(good, "galaxy"))
    assert _practical(blocked, "galaxy") == pytest.approx(_practical(good, "galaxy"))

    session = _session(blocked, "galaxy")
    assert session["state"] == "blocked"
    assert session["value"] == pytest.approx(0.0)
    assert session["blocking_status"]["blocks_plan"] is True
    ownership = _ownership(blocked, "galaxy")
    assert ownership["session_weather_effects"]["legacy_best_object_uses_weather_factor"] is True
    assert ownership["session_weather_effects"]["used_in_observable_target_value"] is False
    assert ownership["session_weather_effects"]["used_in_practical_target_value"] is False


def test_bright_moon_affects_nsom_sky_but_not_legacy_best_object_formula() -> None:
    target = _target("galaxy", "Galaxy", 90)
    low_moon = _compare([target], weather=_weather(90), sky_quality=_sky_quality(3), moon=_moon(10))
    bright_moon = _compare([target], weather=_weather(90), sky_quality=_sky_quality(3), moon=_moon(95))

    assert _legacy_best(bright_moon, "galaxy") == pytest.approx(_legacy_best(low_moon, "galaxy"))
    assert _environment(bright_moon, "galaxy")["lunar_sky_background"] < _environment(low_moon, "galaxy")[
        "lunar_sky_background"
    ]
    assert _effective(bright_moon, "galaxy") < _effective(low_moon, "galaxy")
    unavailable = _entry(bright_moon, "galaxy")["legacy"]["best_object"]["unavailable_components"]
    assert "moon_background_component:not_part_of_best_object_formula" in unavailable


def test_high_light_pollution_affects_nsom_sky_but_not_legacy_best_object_formula() -> None:
    target = _target("galaxy", "Galaxy", 90)
    dark = _compare([target], weather=_weather(90), sky_quality=_sky_quality(3), moon=_moon(10))
    polluted = _compare(
        [target],
        weather=_weather(90),
        sky_quality=_sky_quality(9, radiance=120.0),
        moon=_moon(10),
    )

    assert _legacy_best(polluted, "galaxy") == pytest.approx(_legacy_best(dark, "galaxy"))
    assert _environment(polluted, "galaxy")["static_sky_background"] < _environment(dark, "galaxy")[
        "static_sky_background"
    ]
    assert _effective(polluted, "galaxy") < _effective(dark, "galaxy")
    unavailable = _entry(polluted, "galaxy")["legacy"]["best_object"]["unavailable_components"]
    assert "sky_background_component:not_part_of_best_object_formula" in unavailable


def test_small_and_large_equipment_change_practical_value_only() -> None:
    target = _target("galaxy", "Galaxy", 90)
    small = _compare(
        [target],
        telescope=_telescope(name="Small Manual", aperture_mm=60, focal_length_mm=400, mount="manual"),
    )
    large = _compare(
        [target],
        telescope=_telescope(name="Large GoTo", aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
    )

    assert _observable(small, "galaxy") == pytest.approx(_observable(large, "galaxy"))
    assert _practical(large, "galaxy") > _practical(small, "galaxy")
    assert _legacy_best(large, "galaxy") == pytest.approx(_legacy_best(small, "galaxy"))

    ownership = _ownership(small, "galaxy")
    assert ownership["observer_equipment_effects"]["used_in_observable_target_value"] is False
    assert ownership["observer_equipment_effects"]["used_in_practical_target_value"] is True
    unavailable = _entry(small, "galaxy")["legacy"]["best_object"]["unavailable_components"]
    assert "observer_capability_profile:not_part_of_best_object_formula" in unavailable


def test_confidence_is_metadata_only_and_does_not_change_scores() -> None:
    target = _target("galaxy", "Galaxy", 90)
    low = _compare(
        [target],
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = _compare(
        [target],
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    assert _confidence(low, "galaxy")["value"] < _confidence(high, "galaxy")["value"]
    assert _confidence(low, "galaxy")["score_factor"] is False
    assert _confidence(low, "galaxy")["score_effect"] == pytest.approx(0.0)
    assert _observable(low, "galaxy") == pytest.approx(_observable(high, "galaxy"))
    assert _practical(low, "galaxy") == pytest.approx(_practical(high, "galaxy"))
    assert _legacy_best(low, "galaxy") == pytest.approx(_legacy_best(high, "galaxy"))


def test_best_object_nsom_comparison_does_not_mutate_or_wire_runtime_outputs() -> None:
    targets = [_target("planet", "Pianeta", 86, difficulty="Facile"), _target("galaxy", "Galaxy", 90)]
    before = deepcopy(targets)

    _compare(targets, weather=_weather(90), sky_quality=_sky_quality(8, radiance=45.0), moon=_moon(85))

    assert targets == before
    app_controller = (Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).parents[1] / "app" / "ui").rglob("*.qml")
    )
    assert "BestObjectNsomComparisonService" not in app_controller
    assert "best_object_nsom_comparison" not in app_controller
    assert "BestObjectNsomComparisonService" not in qml_text
    assert "best_object_nsom_comparison" not in qml_text


def _compare(
    targets: list[CelestialObject],
    *,
    weather: WeatherSummary | None = None,
    sky_quality: SkyQuality | None = None,
    telescope: Telescope | None = None,
    moon: MoonSummary | None = None,
    confidence: RecommendationConfidence | None = None,
) -> dict[str, object]:
    return BestObjectNsomComparisonService().compare(
        targets,
        weather=weather or _weather(90),
        sky_quality=sky_quality or _sky_quality(3),
        telescope=telescope or _telescope(),
        moon=moon or _moon(10),
        confidence=confidence,
    )


def _entry(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return next(item for item in comparison["items"] if item["object_id"] == object_id)


def _environment(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return _entry(comparison, object_id)["nsom"]["observation_environment"]


def _ownership(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return _entry(comparison, object_id)["nsom"]["ownership"]


def _session(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return _entry(comparison, object_id)["nsom"]["session_viability"]


def _confidence(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return _entry(comparison, object_id)["nsom"]["recommendation_confidence"]


def _effective(comparison: dict[str, object], object_id: str) -> float:
    return float(_entry(comparison, object_id)["nsom"]["effective_observability"]["value"])


def _observable(comparison: dict[str, object], object_id: str) -> float:
    return float(_entry(comparison, object_id)["nsom"]["observable_target_value"]["value"])


def _practical(comparison: dict[str, object], object_id: str) -> float:
    return float(_entry(comparison, object_id)["nsom"]["practical_target_value"]["value"])


def _legacy_best(comparison: dict[str, object], object_id: str) -> float:
    return float(_entry(comparison, object_id)["legacy"]["best_object"]["score"])


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "8.0",
    difficulty: str = "Media",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="21:00",
        observing_window="21:00 - 02:00",
        notes="Fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
    )


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="Fixture",
        description="Fixture",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="20:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
    )


def _telescope(
    *,
    name: str = "Mak 127",
    aperture_mm: int = 127,
    focal_length_mm: int = 1500,
    mount: str = "manual",
) -> Telescope:
    return Telescope(
        id=name.lower().replace(" ", "-"),
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Reflector",
        mount=mount,
    )
