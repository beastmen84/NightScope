from __future__ import annotations

import inspect
import unittest
from copy import deepcopy
from unittest.mock import Mock

from PySide6.QtCore import QObject

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.nasa_aod_provider import NasaAodResult
from astro_viewer.app.services.openaq_atmosphere_service import LocalAtmosphere
from astro_viewer.app.viewmodels.app_controller import AppController


_WEATHER_SENTINEL = object()


class NsomRuntimeSnapshotTests(unittest.TestCase):
    def test_refresh_nsom_diagnostics_builds_snapshot_from_prepared_objects(self) -> None:
        home_target = _object("messier-M13", "M13", "Ammasso globulare", 82)
        plan_item = _plan_item("messier-M13", "M13", score=82)
        controller = _controller([home_target], [plan_item], best_object=home_target)

        controller._refresh_nsom_diagnostics()

        snapshot = controller._nsom_diagnostic_snapshot
        self.assertEqual(snapshot.notes[:2], ("diagnostic_only", "score_neutral"))
        self.assertIsNotNone(snapshot.confidence)
        self.assertEqual(
            [(target.source, target.object_id) for target in snapshot.targets],
            [
                ("home", "messier-M13"),
                ("planner", "messier-M13"),
                ("best_object", "messier-M13"),
            ],
        )
        self.assertEqual(snapshot.targets[0].name, "M13")
        self.assertEqual(snapshot.targets[0].observable_target_value.value, 82.0)
        self.assertGreater(snapshot.targets[0].practical_target_value.value, 0.0)
        self.assertIn("runtime_snapshot", snapshot.targets[0].observation_opportunity.context)

    def test_refresh_nsom_diagnostics_uses_planner_item_when_target_is_not_prepared(self) -> None:
        plan_item = _plan_item("messier-M99", "M99", score=67)
        controller = _controller([], [plan_item])

        controller._refresh_nsom_diagnostics()

        snapshot = controller._nsom_diagnostic_snapshot
        self.assertEqual(len(snapshot.targets), 1)
        target = snapshot.targets[0]
        self.assertEqual(target.source, "planner")
        self.assertEqual(target.object_id, "messier-M99")
        self.assertEqual(target.name, "M99")
        self.assertEqual(target.observable_target_value.intrinsic_target_quality, 67.0)

    def test_refresh_nsom_diagnostics_does_not_call_heavy_refresh_paths(self) -> None:
        target = _object("messier-M13", "M13", "Ammasso globulare", 82)
        controller = _controller([target], [_plan_item("messier-M13", "M13", score=82)])
        heavy_methods = (
            "_refresh_all",
            "_refresh_astronomy",
            "_refresh_weather_and_conditions",
            "_recalculate_observing_outputs",
            "_refresh_equipment_recommendations_for_current_objects",
            "_refresh_weather_from_timer",
            "_start_weather_refresh",
            "_refresh_local_atmosphere",
            "_schedule_nasa_aod_refresh",
            "_schedule_viirs_sky_quality_refresh",
            "_refresh_sky_compass",
            "_refresh_sky_compass_live",
        )
        for method_name in heavy_methods:
            setattr(controller, method_name, Mock(side_effect=AssertionError(method_name)))

        controller._refresh_nsom_diagnostics()

        for method_name in heavy_methods:
            getattr(controller, method_name).assert_not_called()

    def test_refresh_nsom_diagnostics_does_not_mutate_home_or_planner_objects(self) -> None:
        target = _object("messier-M13", "M13", "Ammasso globulare", 82)
        plan_item = _plan_item("messier-M13", "M13", score=82)
        controller = _controller([target], [plan_item], best_object=target)
        target_before = deepcopy(target)
        plan_before = deepcopy(plan_item)

        controller._refresh_nsom_diagnostics()

        self.assertEqual(target, target_before)
        self.assertEqual(plan_item, plan_before)

    def test_refresh_nsom_diagnostics_does_not_change_object_to_qml_output(self) -> None:
        target = _object("messier-M13", "M13", "Ammasso globulare", 82)
        controller = _controller([target], [])
        before = controller._object_to_qml(target)

        controller._refresh_nsom_diagnostics()

        self.assertEqual(controller._object_to_qml(target), before)
        self.assertNotIn("nsom", controller._object_to_qml(target))

    def test_refresh_nsom_diagnostics_is_safe_with_missing_runtime_data(self) -> None:
        controller = _controller([], [], weather_summary=None)
        controller._nasa_aod_result = NasaAodResult.no_location()
        controller._local_atmosphere = LocalAtmosphere.not_configured()
        controller._sky_quality = None

        controller._refresh_nsom_diagnostics()

        snapshot = controller._nsom_diagnostic_snapshot
        self.assertEqual(snapshot.targets, ())
        self.assertIn("diagnostic_only", snapshot.notes)

    def test_normal_observing_refresh_updates_nsom_snapshot(self) -> None:
        source = inspect.getsource(AppController._recalculate_observing_outputs)

        self.assertIn("self._refresh_nsom_diagnostics()", source)
        self.assertLess(
            source.index("self._notification_service.notifications("),
            source.index("self._refresh_nsom_diagnostics()"),
        )


def _controller(
    home_targets: list[CelestialObject],
    plan_items: list[NightPlanItem],
    *,
    best_object: CelestialObject | None = None,
    weather_summary: WeatherSummary | None | object = _WEATHER_SENTINEL,
) -> AppController:
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._location = ObserverLocation("Test", "Earth", 0.0, 0.0, "UTC")
    controller._conditioned_home_objects = list(home_targets)
    controller._conditioned_deep_sky = list(home_targets)
    controller._visible_planets = []
    controller._deep_sky = list(home_targets)
    controller._solar_system_objects = []
    controller._night_plan = list(plan_items)
    controller._best_object = best_object
    controller._weather_summary = _weather_summary() if weather_summary is _WEATHER_SENTINEL else weather_summary
    controller._nasa_aod_result = NasaAodResult.no_location()
    controller._local_atmosphere = LocalAtmosphere.not_configured()
    controller._sky_quality = None
    controller._moon = None
    controller._seeing_transparency = None
    controller._object_descriptions = {}
    return controller


def _object(object_id: str, name: str, object_type: str, score: int) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="",
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        difficulty="Media",
        recommended_setup_type="telescope",
    )


def _plan_item(object_id: str, name: str, *, score: int) -> NightPlanItem:
    return NightPlanItem(
        time_label="22:00",
        object_id=object_id,
        name=name,
        score=score,
        difficulty="Media",
        setup="Mak 127 + 16 mm",
        direction="Sud",
        image="",
    )


def _weather_summary() -> WeatherSummary:
    return WeatherSummary(
        score="Buono",
        score_value=80,
        explanation="",
        cloud_cover=10,
        precipitation_probability=0,
        wind_kmh=5,
        humidity=50,
        temperature_c=18.0,
        alert="",
    )


if __name__ == "__main__":
    unittest.main()
