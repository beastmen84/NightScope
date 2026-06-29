import inspect

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.observation_conditions_service import ObservationConditionsService
from astro_viewer.app.viewmodels.app_controller import AppController


def _target(
    object_id: str,
    object_type: str,
    score: float,
    difficulty: str,
    best_time: str,
    magnitude: str,
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
        best_time=best_time,
        observing_window=f"{best_time} - 02:00",
        notes="Fixture",
        recommended_setup="",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=round(score),
        score_label="Fixture",
        difficulty=difficulty,
    )


def _planner_fixture_objects() -> list[CelestialObject]:
    return [
        _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5"),
        _target("cluster", "Open Cluster", 76, "Facile", "22:00", "5.0"),
        _target("planet", "Pianeta", 79, "Facile", "23:00", "-1.0"),
        _target("nebula", "Nebula", 78, "Media", "00:30", "7.0"),
    ]


def _weather(score: int, *, cloud_cover: int = 10, precipitation_probability: int = 0) -> WeatherSummary:
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


def _scores(
    planetary: float = 85,
    deep_sky: float = 88,
    seeing: str = "Good",
    transparency: str = "Good",
) -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=planetary,
        deep_sky_score=deep_sky,
        planetary_label=seeing,
        deep_sky_label=transparency,
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
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
        phase_angle=0.0,
    )


def _telescope() -> Telescope:
    return Telescope(
        id="test-scope",
        name="Test Scope",
        aperture_mm=127,
        focal_length_mm=1500,
        optical_type="Mak",
        mount="",
    )


def _plan_summary(plan):
    return [(item.object_id, item.score, item.time_label) for item in plan]


@pytest.mark.parametrize(
    (
        "name",
        "weather",
        "scores",
        "sky_quality",
        "moon",
        "expected",
    ),
    [
        (
            "clear_sky_low_bortle",
            _weather(85),
            _scores(),
            _sky_quality(3),
            _moon(10),
            [
                ("galaxy", 87, "21:00 sera"),
                ("cluster", 96, "22:00 sera"),
                ("planet", 96, "23:00 sera"),
                ("nebula", 85, "00:30 notte"),
            ],
        ),
        (
            "high_bortle",
            _weather(85),
            _scores(),
            _sky_quality(8),
            _moon(10),
            [
                ("galaxy", 62, "21:00 sera"),
                ("cluster", 84, "22:00 sera"),
                ("planet", 96, "23:00 sera"),
                ("nebula", 65, "00:30 notte"),
            ],
        ),
        (
            "high_moon_illumination",
            _weather(85),
            _scores(),
            _sky_quality(3),
            _moon(95),
            [
                ("galaxy", 53, "21:00 sera"),
                ("cluster", 86, "22:00 sera"),
                ("planet", 96, "23:00 sera"),
                ("nebula", 62, "00:30 notte"),
            ],
        ),
        (
            "poor_weather_score",
            _weather(35),
            _scores(),
            _sky_quality(3),
            _moon(10),
            [
                ("galaxy", 51, "21:00 sera"),
                ("cluster", 56, "22:00 sera"),
                ("planet", 56, "23:00 sera"),
                ("nebula", 50, "00:30 notte"),
            ],
        ),
        (
            "unknown_weather_blocks_plan",
            _weather(0),
            _scores(),
            _sky_quality(3),
            _moon(10),
            [],
        ),
        (
            "good_seeing_via_advanced_scores",
            _weather(85),
            _scores(95, 95, "Excellent", "Excellent"),
            _sky_quality(3),
            _moon(10),
            [
                ("galaxy", 89, "21:00 sera"),
                ("cluster", 98, "22:00 sera"),
                ("planet", 100, "23:00 sera"),
                ("nebula", 87, "00:30 notte"),
            ],
        ),
        (
            "poor_seeing_via_advanced_scores",
            _weather(85),
            _scores(45, 45, "Poor", "Poor"),
            _sky_quality(3),
            _moon(10),
            [
                ("galaxy", 73, "21:00 sera"),
                ("cluster", 80, "22:00 sera"),
                ("planet", 82, "23:00 sera"),
                ("nebula", 71, "00:30 notte"),
            ],
        ),
    ],
)
def test_planner_output_current_conditions_matrix_is_characterized(
    name,
    weather,
    scores,
    sky_quality,
    moon,
    expected,
):
    del name
    plan = NightPlannerService().plan(
        _planner_fixture_objects(),
        weather=weather,
        scores=scores,
        sky_quality=sky_quality,
        telescope=_telescope(),
        moon=moon,
    )

    assert _plan_summary(plan) == expected


def test_planner_orders_galaxy_vs_open_cluster_under_bright_moon():
    galaxy = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    cluster = _target("cluster", "Open Cluster", 76, "Facile", "22:00", "5.0")
    scores = _scores()
    weather = _weather(85)
    sky_quality = _sky_quality(3)
    moon = _moon(95)

    galaxy_score = NightPlannerService._planner_score(galaxy, weather, scores, sky_quality, _telescope(), moon)
    cluster_score = NightPlannerService._planner_score(cluster, weather, scores, sky_quality, _telescope(), moon)

    assert round(galaxy_score, 2) == 53.36
    assert round(cluster_score, 2) == 85.78
    assert cluster_score > galaxy_score


def test_planner_orders_nebula_vs_cluster_under_high_light_pollution():
    nebula = _target("nebula", "Nebula", 78, "Media", "00:30", "7.0")
    cluster = _target("cluster", "Open Cluster", 76, "Facile", "22:00", "5.0")
    scores = _scores()
    weather = _weather(85)
    sky_quality = _sky_quality(8)
    moon = _moon(10)

    nebula_score = NightPlannerService._planner_score(nebula, weather, scores, sky_quality, _telescope(), moon)
    cluster_score = NightPlannerService._planner_score(cluster, weather, scores, sky_quality, _telescope(), moon)

    assert round(nebula_score, 2) == 64.71
    assert round(cluster_score, 2) == 83.76
    assert cluster_score > nebula_score


def test_planner_orders_planet_vs_deep_sky_under_poor_sky_quality():
    planet = _target("planet", "Pianeta", 79, "Facile", "23:00", "-1.0")
    galaxy = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    scores = _scores()
    weather = _weather(85)
    sky_quality = _sky_quality(9)
    moon = _moon(90)

    planet_score = NightPlannerService._planner_score(planet, weather, scores, sky_quality, _telescope(), moon)
    galaxy_score = NightPlannerService._planner_score(galaxy, weather, scores, sky_quality, _telescope(), moon)

    assert round(planet_score, 2) == 96.31
    assert round(galaxy_score, 2) == 24.42
    assert planet_score > galaxy_score


def test_current_moon_penalty_boundaries_are_characterized():
    galaxy = _target("galaxy", "Galaxy", 80, "Media", "21:00", "8.5")

    assert NightPlannerService.moon_penalty(galaxy, _moon(0)) == 0.0
    assert NightPlannerService.moon_penalty(galaxy, _moon(25)) == 0.0
    assert NightPlannerService.moon_penalty(galaxy, _moon(26)) == pytest.approx(0.5066666667)
    assert NightPlannerService.moon_penalty(galaxy, _moon(100)) == 38.0


def test_planner_moon_score_matches_observation_conditions_service():
    galaxy = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    moon = _moon(95)
    service_breakdown = ObservationConditionsService().moon_adjusted_score(galaxy, moon)
    planner_breakdown = NightPlannerService._moon_condition_breakdown(galaxy, moon)

    assert planner_breakdown == service_breakdown
    assert NightPlannerService.moon_penalty(galaxy, moon) == service_breakdown.moon_penalty
    assert NightPlannerService.moon_adjusted_score(galaxy, moon) == service_breakdown.adjusted_score
    assert planner_breakdown.applied_components == ("moon",)


def test_planner_condition_refactor_keeps_weather_and_difficulty_local():
    score_source = inspect.getsource(NightPlannerService._planner_score)
    breakdown_source = inspect.getsource(NightPlannerService._planner_score_breakdown)
    pollution_source = inspect.getsource(NightPlannerService._pollution_penalty)

    assert "_planner_score_breakdown" in score_source
    assert "_planner_condition_breakdown" in breakdown_source
    assert "_weather_factor" in breakdown_source
    assert "difficulty_factor" in breakdown_source
    assert "planner_pollution_penalty" in pollution_source
    assert "apply_pollution" not in score_source + breakdown_source
    assert "deep_sky_pollution" not in score_source + breakdown_source


def test_current_pollution_penalty_boundaries_are_characterized():
    galaxy = _target("galaxy", "Galaxy", 80, "Media", "21:00", "8.5")

    assert NightPlannerService._pollution_penalty(galaxy, _sky_quality(4)) == 0.0
    assert NightPlannerService._pollution_penalty(galaxy, _sky_quality(5)) == pytest.approx(6.6)
    assert NightPlannerService._pollution_penalty(galaxy, _sky_quality(7)) == pytest.approx(19.8)
    assert NightPlannerService._pollution_penalty(galaxy, _sky_quality(4, radiance=0)) == 0.0
    assert round(NightPlannerService._pollution_penalty(galaxy, _sky_quality(4, radiance=20)), 3) == 19.635
    assert round(NightPlannerService._pollution_penalty(galaxy, _sky_quality(4, radiance=1000)), 3) == 44.556


def test_planner_pollution_penalty_matches_observation_conditions_service():
    targets = [
        _target("planet", "Pianeta", 79, "Facile", "23:00", "-1.0"),
        _target("galaxy", "Galaxy", 80, "Media", "21:00", "8.5"),
        _target("nebula", "Nebula", 78, "Media", "00:30", "7.0"),
        _target("globular", "Globular Cluster", 76, "Media", "22:00", "5.8"),
        _target("cluster", "Open Cluster", 76, "Facile", "22:00", "5.0"),
    ]
    sky_quality = _sky_quality(8, radiance=20)

    for target in targets:
        assert NightPlannerService._pollution_penalty(
            target,
            sky_quality,
        ) == ObservationConditionsService.planner_pollution_penalty(target, sky_quality)


def test_planner_condition_breakdown_matches_moon_and_pollution_wrappers():
    galaxy = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    sky_quality = _sky_quality(8, radiance=20)
    moon = _moon(95)

    breakdown = NightPlannerService._planner_condition_breakdown(galaxy, sky_quality, moon)

    assert breakdown.object_id == "galaxy"
    assert breakdown.base_score == galaxy.score
    assert breakdown.moon_penalty == NightPlannerService.moon_penalty(galaxy, moon)
    assert breakdown.pollution_penalty == NightPlannerService._pollution_penalty(galaxy, sky_quality)
    assert breakdown.applied_components == ("moon", "planner_light_pollution")
    assert "moon:illumination=95" in breakdown.diagnostic_notes
    assert "planner_light_pollution:active" in breakdown.diagnostic_notes
    assert "weather:planner_owned" in breakdown.diagnostic_notes
    assert "difficulty:planner_owned" in breakdown.diagnostic_notes


def test_planner_condition_breakdown_is_neutral_for_planets_under_low_moon_and_good_sky():
    planet = _target("planet", "Pianeta", 79, "Facile", "23:00", "-1.0")
    sky_quality = _sky_quality(3)
    moon = _moon(10)

    breakdown = NightPlannerService._planner_condition_breakdown(planet, sky_quality, moon)

    assert breakdown.moon_penalty == 0.0
    assert breakdown.pollution_penalty == 0.0
    assert breakdown.applied_components == ()
    assert "moon:neutral" in breakdown.diagnostic_notes
    assert "planner_light_pollution:neutral" in breakdown.diagnostic_notes


def test_planner_score_breakdown_matches_current_formula():
    galaxy = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    weather = _weather(85)
    scores = _scores()
    sky_quality = _sky_quality(8, radiance=20)
    moon = _moon(95)
    telescope = _telescope()

    breakdown = NightPlannerService._planner_score_breakdown(
        galaxy,
        weather,
        scores,
        sky_quality,
        telescope,
        moon,
    )

    assert breakdown.object_id == "galaxy"
    assert breakdown.base_score == 82
    assert breakdown.category_score == 88
    assert breakdown.weather_score == 85
    assert breakdown.object_score_contribution == pytest.approx(39.36)
    assert breakdown.category_score_contribution == pytest.approx(29.92)
    assert breakdown.weather_score_contribution == pytest.approx(15.3)
    assert breakdown.aperture_bonus == pytest.approx(127 / 18)
    assert breakdown.moon_penalty == NightPlannerService.moon_penalty(galaxy, moon)
    assert breakdown.pollution_penalty == NightPlannerService._pollution_penalty(galaxy, sky_quality)
    assert breakdown.difficulty_factor == 0.95
    assert breakdown.weather_factor == 1.0
    assert breakdown.raw_score_before_weather == pytest.approx(
        breakdown.raw_score_before_difficulty * breakdown.difficulty_factor
    )
    assert breakdown.final_score == pytest.approx(breakdown.raw_score_before_weather * breakdown.weather_factor)
    assert breakdown.final_score == pytest.approx(
        NightPlannerService._planner_score(galaxy, weather, scores, sky_quality, telescope, moon)
    )
    assert breakdown.conditions.applied_components == ("moon", "planner_light_pollution")


def test_planner_score_breakdown_keeps_weather_factor_after_raw_score():
    target = _target("galaxy", "Galaxy", 80, "Difficile", "21:00", "8.5")
    weather = _weather(35)
    scores = _scores()
    sky_quality = _sky_quality(3)
    moon = _moon(10)

    breakdown = NightPlannerService._planner_score_breakdown(
        target,
        weather,
        scores,
        sky_quality,
        _telescope(),
        moon,
    )

    assert breakdown.difficulty_factor == 0.75
    assert breakdown.weather_factor == 0.65
    assert breakdown.raw_score_before_weather == pytest.approx(
        breakdown.raw_score_before_difficulty * breakdown.difficulty_factor
    )
    assert breakdown.final_score == pytest.approx(
        breakdown.raw_score_before_difficulty * breakdown.difficulty_factor * breakdown.weather_factor
    )


@pytest.mark.parametrize(
    ("score", "expected_factor"),
    [
        (24, 0.35),
        (25, 0.65),
        (49, 0.65),
        (50, 0.85),
        (69, 0.85),
        (70, 1.0),
    ],
)
def test_current_weather_factor_boundaries_are_characterized(score, expected_factor):
    assert NightPlannerService._weather_factor(_weather(score)) == expected_factor


def test_current_difficulty_factor_is_part_of_planner_ranking():
    scores = {}
    for difficulty in ("Facile", "Media", "Difficile", "Altro"):
        target = _target(difficulty, "Galaxy", 80, difficulty, "21:00", "8.5")
        planner_score = NightPlannerService._planner_score(
            target,
            _weather(85),
            _scores(),
            _sky_quality(3),
            _telescope(),
            _moon(10),
        )
        scores[difficulty] = round(planner_score, 2)

    assert scores == {
        "Facile": 97.93,
        "Media": 86.14,
        "Difficile": 68.01,
        "Altro": 77.07,
    }


def test_app_controller_home_moon_adjusted_output_remains_characterized():
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._moon = _moon(95)

    adjusted = controller._moon_adjusted_objects(
        [
            _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5"),
            _target("cluster", "Open Cluster", 76, "Facile", "22:00", "5.0"),
        ]
    )

    assert [(item.id, item.score) for item in adjusted] == [
        ("cluster", 67),
        ("galaxy", 47),
    ]


def test_sky_compass_live_refresh_source_still_avoids_planner_and_scoring_paths():
    source = inspect.getsource(AppController._refresh_sky_compass_live)

    assert "_sky_compass_candidates" not in source
    assert "_refresh_observing_outputs" not in source
    assert "_refresh_weather_and_conditions" not in source
    assert "_refresh_astronomy" not in source
    assert "_refresh_all" not in source
    assert "_planner_score" not in source
    assert "_night_planner_service" not in source
