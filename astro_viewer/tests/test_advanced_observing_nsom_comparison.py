from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.advanced_observing_nsom_comparison import (
    AdvancedObservingNsomComparisonService,
)
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService


def test_advanced_observing_nsom_comparison_is_strict_json_and_developer_only() -> None:
    comparison = _compare()

    json.dumps(comparison, allow_nan=False)
    assert comparison["metadata"]["developer_only"] is True
    assert comparison["metadata"]["runtime_wiring"] is False
    assert comparison["metadata"]["reference_only"] is True
    assert comparison["metadata"]["score_parity_expected"] is False
    assert comparison["metadata"]["side_effects"] == {
        "file_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "advanced_scores_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "sky_compass_changed": False,
    }
    assert comparison["legacy"]["planetary"]["formula"].startswith(
        "round(weather.score_value*0.36"
    )
    assert comparison["legacy"]["deep_sky"]["formula"].startswith(
        "round(weather.score_value*0.34"
    )
    assert comparison["nsom"]["planetary_reference"]["reference_only"] is True
    assert comparison["nsom"]["deep_sky_reference_summary"]["reference_only"] is True


def test_legacy_formula_projection_matches_advanced_observing_service() -> None:
    weather = _weather(82, wind_kmh=18)
    seeing = _seeing(seeing_score=77, transparency_score=64)
    sky_quality = _sky_quality(5)
    moon = _moon(42)

    comparison = _compare(weather=weather, seeing=seeing, sky_quality=sky_quality, moon=moon)
    scores = AdvancedObservingService().scores(weather, seeing, sky_quality, moon)

    assert comparison["legacy"]["advanced_scores"]["planetary_score"] == scores.planetary_score
    assert comparison["legacy"]["advanced_scores"]["deep_sky_score"] == scores.deep_sky_score
    assert comparison["legacy"]["planetary"]["score"] == scores.planetary_score
    assert comparison["legacy"]["deep_sky"]["score"] == scores.deep_sky_score
    assert comparison["legacy"]["planetary"]["components"]["weather"]["weight"] == pytest.approx(0.36)
    assert comparison["legacy"]["deep_sky"]["components"]["transparency"]["weight"] == pytest.approx(0.30)


def test_poor_weather_changes_legacy_scores_and_session_not_reference_observable_values() -> None:
    good = _compare(weather=_weather(90, cloud_cover=10, precipitation_probability=0))
    poor = _compare(weather=_weather(20, cloud_cover=95, precipitation_probability=80))

    assert poor["legacy"]["planetary"]["score"] < good["legacy"]["planetary"]["score"]
    assert poor["legacy"]["deep_sky"]["score"] < good["legacy"]["deep_sky"]["score"]
    assert _planet_observable(poor) == pytest.approx(_planet_observable(good))
    assert _deep_sky_average(poor) == pytest.approx(_deep_sky_average(good))

    session = poor["nsom"]["session_viability"]
    assert session["state"] == "blocked"
    assert session["value"] == pytest.approx(0.0)
    assert session["score_effect_on_reference_observable_values"] == pytest.approx(0.0)
    assert poor["legacy"]["planetary"]["weather_cap"] <= 30
    assert poor["legacy"]["deep_sky"]["weather_cap"] <= 30


def test_bright_moon_degrades_deep_sky_reference_but_not_planetary_sky_background() -> None:
    low_moon = _compare(moon=_moon(5))
    bright_moon = _compare(moon=_moon(95))

    assert _planet_env(bright_moon)["lunar_sky_background"] == pytest.approx(1.0)
    assert _planet_env(low_moon)["lunar_sky_background"] == pytest.approx(1.0)
    assert _deep_sky_average(bright_moon) < _deep_sky_average(low_moon)
    assert bright_moon["legacy"]["deep_sky"]["score"] < low_moon["legacy"]["deep_sky"]["score"]
    assert bright_moon["legacy"]["planetary"]["score"] <= low_moon["legacy"]["planetary"]["score"]
    assert "moon_mixed_into_planetary_category_score" in bright_moon["legacy"]["planetary"][
        "ownership_mixing"
    ]


def test_high_light_pollution_degrades_deep_sky_reference_but_not_planetary_reference() -> None:
    dark = _compare(sky_quality=_sky_quality(3, radiance=None))
    polluted = _compare(sky_quality=_sky_quality(9, radiance=120.0))

    assert _planet_env(polluted)["static_sky_background"] == pytest.approx(1.0)
    assert _planet_observable(polluted) == pytest.approx(_planet_observable(dark))
    assert _deep_sky_average(polluted) < _deep_sky_average(dark)
    assert polluted["legacy"]["deep_sky"]["score"] < dark["legacy"]["deep_sky"]["score"]
    assert polluted["legacy"]["planetary"]["score"] == pytest.approx(dark["legacy"]["planetary"]["score"])


def test_confidence_is_metadata_only_and_does_not_change_scores_or_reference_values() -> None:
    low = _compare(
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0)
    )
    high = _compare(
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0)
    )

    assert low["nsom"]["recommendation_confidence"]["value"] < high["nsom"][
        "recommendation_confidence"
    ]["value"]
    assert low["nsom"]["recommendation_confidence"]["score_factor"] is False
    assert low["nsom"]["recommendation_confidence"]["score_effect"] == pytest.approx(0.0)
    assert low["legacy"]["planetary"]["score"] == high["legacy"]["planetary"]["score"]
    assert low["legacy"]["deep_sky"]["score"] == high["legacy"]["deep_sky"]["score"]
    assert _planet_observable(low) == pytest.approx(_planet_observable(high))
    assert _deep_sky_average(low) == pytest.approx(_deep_sky_average(high))


def test_advanced_observing_nsom_comparison_does_not_mutate_or_wire_runtime_outputs() -> None:
    weather = _weather(90)
    seeing = _seeing()
    sky_quality = _sky_quality(8, radiance=45.0)
    moon = _moon(85)
    before = deepcopy((weather, seeing, sky_quality, moon))

    _compare(weather=weather, seeing=seeing, sky_quality=sky_quality, moon=moon)

    assert (weather, seeing, sky_quality, moon) == before
    app_controller = (Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).parents[1] / "app" / "ui").rglob("*.qml")
    )
    assert "AdvancedObservingNsomComparisonService" not in app_controller
    assert "advanced_observing_nsom_comparison" not in app_controller
    assert "AdvancedObservingNsomComparisonService" not in qml_text
    assert "advanced_observing_nsom_comparison" not in qml_text


def _compare(
    *,
    weather: WeatherSummary | None = None,
    seeing: SeeingTransparency | None = None,
    sky_quality: SkyQuality | None = None,
    moon: MoonSummary | None = None,
    confidence: RecommendationConfidence | None = None,
) -> dict[str, object]:
    return AdvancedObservingNsomComparisonService().compare(
        weather=weather or _weather(90),
        seeing=seeing or _seeing(),
        sky_quality=sky_quality or _sky_quality(3),
        moon=moon or _moon(10),
        confidence=confidence,
    )


def _planet_env(comparison: dict[str, object]) -> dict[str, object]:
    return comparison["nsom"]["planetary_reference"]["observation_environment"]


def _planet_observable(comparison: dict[str, object]) -> float:
    return float(comparison["nsom"]["planetary_reference"]["observable_target_value"]["value"])


def _deep_sky_average(comparison: dict[str, object]) -> float:
    return float(comparison["nsom"]["deep_sky_reference_summary"]["average_observable_target_value"])


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
    wind_kmh: int = 5,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=wind_kmh,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _seeing(
    *,
    seeing_score: int = 85,
    transparency_score: int = 82,
) -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Good",
        transparency="Good",
        seeing_score=seeing_score,
        transparency_score=transparency_score,
        explanation="Fixture",
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
