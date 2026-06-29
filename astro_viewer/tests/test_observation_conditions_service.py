from __future__ import annotations

import math
from dataclasses import replace

from astro_viewer.app.models.equipment import Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.observation_conditions_service import ObservationConditionsService
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_moon_adjustment_matches_existing_planner_formula_for_target_types() -> None:
    service = ObservationConditionsService()
    moon = _moon("82%")
    targets = [
        _target("mars", "Marte", "Pianeta", 78),
        _target("m31", "M31", "Galassia", 78),
        _target("m42", "M42", "Nebula", 78),
        _target("m13", "M13", "Globular Cluster", 78),
        _target("m45", "M45", "Open Cluster", 78),
    ]

    for target in targets:
        breakdown = service.moon_adjusted_score(target, moon)

        assert breakdown.adjusted_score == NightPlannerService.moon_adjusted_score(target, moon)
        assert service.apply_moon_adjustment(target, moon).target.score == breakdown.adjusted_score
        if target.object_type == "Pianeta":
            assert breakdown.applied_components == ()
            assert breakdown.moon_penalty == 0.0
        else:
            assert breakdown.applied_components == ("moon",)
            assert breakdown.moon_penalty > 0.0


def test_pollution_context_matches_legacy_high_bortle_behaviour() -> None:
    targets = _deep_sky_targets()
    sky_quality = _sky_quality(bortle=8)
    service = ObservationConditionsService()

    assert service.apply_deep_sky_pollution_context(targets, sky_quality) == _legacy_pollution_context(
        targets,
        sky_quality,
    )


def test_pollution_context_matches_legacy_high_viirs_behaviour() -> None:
    targets = _deep_sky_targets()
    sky_quality = _sky_quality(bortle=5, radiance=180.0)
    service = ObservationConditionsService()

    assert service.apply_deep_sky_pollution_context(targets, sky_quality) == _legacy_pollution_context(
        targets,
        sky_quality,
    )


def test_pollution_context_preserves_good_low_radiance_sky() -> None:
    targets = _deep_sky_targets()
    sky_quality = _sky_quality(bortle=4, radiance=8.0)
    service = ObservationConditionsService()

    assert service.apply_deep_sky_pollution_context(targets, sky_quality) == targets


def test_pollution_context_preserves_missing_sky_quality_context() -> None:
    targets = _deep_sky_targets()
    service = ObservationConditionsService()

    assert service.apply_deep_sky_pollution_context(targets, None) == targets


def test_deep_sky_object_ordering_matches_legacy_pollution_context() -> None:
    targets = [_target(f"m{i}", f"M{i}", "Galaxy", 95 - i * 3, magnitude="8.8") for i in range(12)]
    sky_quality = _sky_quality(bortle=8, radiance=140.0)
    service = ObservationConditionsService()

    updated = service.apply_deep_sky_pollution_context(targets, sky_quality)
    legacy = _legacy_pollution_context(targets, sky_quality)

    assert [item.id for item in updated] == [item.id for item in legacy]
    assert len(updated) == len(legacy) == 10


def test_app_controller_home_detail_conditioned_object_output_matches_legacy_formula() -> None:
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._moon = _moon("86%")
    target = _target("m31", "M31", "Galassia", 82)

    conditioned = controller._moon_adjusted_object(target)
    expected_score = NightPlannerService.moon_adjusted_score(target, controller._moon)
    expected = replace(
        target,
        score=expected_score,
        score_label=ObservingScoreService.score_label(expected_score),
    )

    assert conditioned == expected


def test_app_controller_deep_sky_pollution_context_matches_legacy_formula() -> None:
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._sky_quality = _sky_quality(bortle=8, radiance=120.0)
    targets = _deep_sky_targets()

    assert controller._apply_deep_sky_pollution_context(targets) == _legacy_pollution_context(
        targets,
        controller._sky_quality,
    )


def test_planner_output_characterization_is_unchanged_on_fixture() -> None:
    planner = NightPlannerService()
    objects = [
        _target("venus", "Venere", "Pianeta", 83, best_time="20:45", difficulty="Facile"),
        _target("m24", "M24", "Open Cluster", 74, best_time="00:30", difficulty="Media"),
        _target("saturn", "Saturno", "Pianeta", 88, best_time="01:30", difficulty="Facile"),
    ]

    plan = planner.plan(
        objects,
        _weather_summary(score=82),
        AdvancedObservingScores(80, 76, "Buona", "Buona", "fixture"),
        _sky_quality(bortle=5),
        _telescope(),
        _moon("24%"),
    )

    assert [item.object_id for item in plan] == ["venus", "m24", "saturn"]
    assert [item.time_label for item in plan] == ["20:45 sera", "00:30 notte", "01:30 notte"]


def test_best_object_characterization_is_unchanged_on_fixture() -> None:
    service = ObservingScoreService()
    objects = [
        _target("easy", "Easy", "Open Cluster", 70, difficulty="Facile"),
        _target("hard", "Hard", "Galaxy", 90, difficulty="Difficile"),
        _target("medium", "Medium", "Globular Cluster", 78, difficulty="Media"),
    ]

    best = service.best_object(objects, _weather_summary(score=70))

    assert best is not None
    assert best.id == "easy"


def test_equipment_recommendation_characterization_is_unchanged_on_fixture() -> None:
    service = EquipmentService()

    suggestion = service.suggest_for_profile(
        _target(
            "mars",
            "Marte",
            "Pianeta",
            82,
            magnitude="-1.0",
            max_altitude="55 gradi",
            recommended_observation_type="HighMagnification",
        ),
        [_telescope()],
        [
            Eyepiece(
                "zoom",
                "Baader Hyperion Zoom",
                24.0,
                68.0,
                eyepiece_type="Zoom",
                min_focal_length_mm=8.0,
                max_focal_length_mm=24.0,
                zoom_click_positions_mm=(24.0, 20.0, 16.0, 12.0, 8.0),
            )
        ],
        [],
        _seeing(score=50),
        _sky_quality(bortle=5),
        [],
    )

    assert suggestion["setupText"] == "Mak 127 + Baader Hyperion Zoom @ 16 mm"
    assert suggestion["bestEyepiece"] == "Baader Hyperion Zoom"
    assert suggestion["selectionScore"] > 70


def test_observation_conditions_service_does_not_import_openaq_or_nasa_aod() -> None:
    import astro_viewer.app.services.observation_conditions_service as module

    names = set(module.__dict__)

    assert "OpenAQLocalAtmosphereService" not in names
    assert "NasaAodProvider" not in names
    assert "LocalAtmosphere" not in names
    assert "NasaAodResult" not in names


def _target(
    object_id: str,
    name: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "7.8",
    max_altitude: str = "48 gradi",
    best_time: str = "22:00",
    difficulty: str = "Media",
    recommended_observation_type: str = "General",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude=max_altitude,
        direction="Sud",
        best_time=best_time,
        observing_window=f"{best_time} - 02:00",
        notes="Nota.",
        recommended_setup="",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label=ObservingScoreService.score_label(score),
        difficulty=difficulty,
        apparent_size="20 arcmin",
        max_angular_size_deg=0.33,
        recommended_observation_type=recommended_observation_type,
    )


def _deep_sky_targets() -> list[CelestialObject]:
    return [
        _target("m31", "M31", "Galaxy", 88, magnitude="3.4", recommended_observation_type="WideField"),
        _target("m42", "M42", "Nebula", 84, magnitude="4.0", recommended_observation_type="General"),
        _target("m13", "M13", "Globular Cluster", 79, magnitude="5.8"),
        _target("m45", "M45", "Open Cluster", 75, magnitude="1.6", recommended_observation_type="WideField"),
        _target("m101", "M101", "Galaxy", 64, magnitude="9.0"),
    ]


def _moon(illumination: str) -> MoonSummary:
    return MoonSummary("Gibbosa", illumination, "18:00", "05:00", "Luna luminosa.", "", 0.0)


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.0,
        sky_brightness=19.0,
        source="fixture",
        description="fixture",
        viirs_radiance=radiance,
    )


def _weather_summary(score: int) -> WeatherSummary:
    return WeatherSummary(
        score=ObservingScoreService.score_label(score),
        score_value=score,
        explanation="fixture",
        cloud_cover=20,
        precipitation_probability=5,
        wind_kmh=8,
        humidity=55,
        temperature_c=14.0,
        alert="fixture",
    )


def _telescope() -> Telescope:
    return Telescope("mak127", "Mak 127", 127, 1500, "Maksutov", "planetary")


def _seeing(score: int) -> SeeingTransparency:
    return SeeingTransparency("Average", "Average", score, 60, "fixture")


def _legacy_pollution_context(
    targets: list[CelestialObject],
    sky_quality: SkyQuality | None,
) -> list[CelestialObject]:
    if not sky_quality:
        return targets
    radiance = sky_quality.viirs_radiance
    if radiance is None and sky_quality.bortle_class < 7:
        return targets
    if radiance is not None and radiance < 20 and sky_quality.bortle_class < 7:
        return targets

    updated = []
    for item in targets:
        lower_type = item.object_type.lower()
        penalty = _legacy_pollution_base_penalty(sky_quality)
        if "galaxy" in lower_type or "galassia" in lower_type:
            penalty *= 2.0
        elif "nebula" in lower_type and "cluster" not in lower_type:
            penalty *= 1.6
        elif "globular" in lower_type:
            penalty *= 1.15
        elif "open" in lower_type or "cluster" in lower_type:
            penalty *= 0.55
        try:
            magnitude = float(item.magnitude)
        except ValueError:
            magnitude = 10.0
        if magnitude >= 8.5:
            penalty += 12
        surface_brightness = _surface_brightness_proxy(item)
        if surface_brightness and surface_brightness >= 13.5:
            penalty += 8
        score = max(0, round(item.score - penalty))
        note = item.notes
        urban_note = "Cielo luminoso: visibilità limitata, serve trasparenza buona e schermare luci dirette."
        if urban_note not in note:
            note = f"{urban_note} {note}"
        updated.append(
            replace(
                item,
                score=score,
                score_label=ObservingScoreService.score_label(score),
                visible=item.visible and score > 10,
                notes=note,
            )
        )
    return sorted([item for item in updated if item.visible], key=lambda item: item.score, reverse=True)[:10]


def _legacy_pollution_base_penalty(sky_quality: SkyQuality) -> float:
    radiance = sky_quality.viirs_radiance
    bortle_penalty = max(0.0, (sky_quality.bortle_class - 6) * 8.0)
    if radiance is None:
        return max(6.0, bortle_penalty)
    radiance_penalty = min(24.0, math.log10(max(0.0, radiance) + 1.0) * 6.0)
    return max(6.0, bortle_penalty, radiance_penalty)


def _surface_brightness_proxy(item: CelestialObject) -> float | None:
    try:
        magnitude = float(item.magnitude)
    except ValueError:
        return None
    size_arcmin = 20.0
    return magnitude + 2.5 * math.log10(max(size_arcmin * size_arcmin, 1.0))
