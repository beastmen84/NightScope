from __future__ import annotations

import inspect
import json
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch

from PySide6.QtCore import QObject

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.models.observing import CelestialObject, MoonGeometrySummary
from astro_viewer.app.models.sky import NightPlanItem, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.light_pollution_service import LightPollutionService
from astro_viewer.app.services.nasa_aod_provider import NasaAodResult
from astro_viewer.app.services.night_planner_service import NightPlannerService
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
            [(target.source, target.object_id, target.observable_target_value.intrinsic_target_quality) for target in snapshot.targets],
            [
                ("home", "messier-M13", 82.0),
                ("planner", "messier-M13", 82.0),
                ("best_object", "messier-M13", 82.0),
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
        self.assertEqual(dict(target.runtime_fields)["setup"], "Mak 127 + 16 mm")
        self.assertEqual(dict(target.runtime_fields)["time_label"], "22:00")

    def test_export_nsom_diagnostics_uses_existing_snapshot_only(self) -> None:
        home_target = _object("messier-M13", "M13", "Ammasso globulare", 82)
        plan_item = _plan_item("messier-M13", "M13", score=84)
        controller = _controller([home_target], [plan_item], best_object=home_target)
        controller._refresh_nsom_diagnostics()
        controller._refresh_nsom_diagnostics = Mock(side_effect=AssertionError("no refresh"))

        exported = controller._export_nsom_diagnostics()

        self.assertEqual(exported["metadata"]["schema"], "nsom_diagnostic_snapshot")
        self.assertTrue(exported["metadata"]["diagnostic_only"])
        self.assertEqual(exported["location"]["city"], "Test")
        self.assertIn("confidenceInputs", exported)
        self.assertEqual(len(exported["targets"]), 3)
        planner_targets = exported["planner"]["targets"]
        self.assertEqual(len(planner_targets), 1)
        self.assertEqual(planner_targets[0]["observableTargetValue"]["intrinsicTargetQuality"], 84.0)
        self.assertEqual(planner_targets[0]["runtimeFields"]["score"], 84)
        self.assertEqual(planner_targets[0]["runtimeFields"]["prepared_target_score"], 82)
        self.assertEqual(planner_targets[0]["runtimeFields"]["setup"], "Mak 127 + 16 mm")
        controller._refresh_nsom_diagnostics.assert_not_called()

    def test_refresh_nsom_diagnostics_confidence_distinguishes_real_viirs_and_missing_moon_geometry(self) -> None:
        controller = _controller([], [])
        controller._sky_quality = SkyQuality(
            bortle_class=4,
            limiting_magnitude=6.1,
            sky_brightness=21.0,
            source="Local estimate",
            description="",
        )

        controller._refresh_nsom_diagnostics()

        self.assertEqual(controller._nsom_diagnostic_snapshot.confidence.viirs_confidence, 0.0)
        self.assertIsNone(controller._nsom_diagnostic_snapshot.confidence.moon_geometry_confidence)
        confidence_inputs = dict(controller._nsom_diagnostic_snapshot.confidence_inputs)
        self.assertFalse(confidence_inputs["viirs_available"])
        self.assertEqual(confidence_inputs["viirs_source_type"], "fallback")

        controller._sky_quality = SkyQuality(
            bortle_class=4,
            limiting_magnitude=6.1,
            sky_brightness=21.0,
            source="World Atlas / VIIRS preprocessed local dataset",
            description="",
        )

        controller._refresh_nsom_diagnostics()

        self.assertEqual(controller._nsom_diagnostic_snapshot.confidence.viirs_confidence, 0.0)
        confidence_inputs = dict(controller._nsom_diagnostic_snapshot.confidence_inputs)
        self.assertFalse(confidence_inputs["viirs_available"])
        self.assertEqual(confidence_inputs["viirs_source_type"], "local_preprocessed")

        controller._sky_quality = SkyQuality(
            bortle_class=4,
            limiting_magnitude=6.1,
            sky_brightness=21.0,
            source="NASA Black Marble VNP46A3",
            description="",
            viirs_radiance=1.2,
        )

        controller._refresh_nsom_diagnostics()

        self.assertEqual(controller._nsom_diagnostic_snapshot.confidence.viirs_confidence, 1.0)
        confidence_inputs = dict(controller._nsom_diagnostic_snapshot.confidence_inputs)
        self.assertTrue(confidence_inputs["viirs_available"])
        self.assertEqual(confidence_inputs["viirs_source_type"], "provider")

    def test_refresh_nsom_diagnostics_exports_local_moon_geometry_score_neutrally(self) -> None:
        home_target = _object("messier-M13", "M13", "Ammasso globulare", 82)
        controller = _controller([home_target], [_plan_item("messier-M13", "M13", score=82)], best_object=home_target)
        controller._astronomy_engine = _MoonGeometryEngine(
            MoonGeometrySummary(
                object_id="messier-M13",
                moon_altitude_deg=41.5,
                moon_target_separation_deg=72.25,
                moon_above_horizon=True,
                moon_visible_during_target_window=True,
                moon_set_before_target_window=False,
                sample_count=4,
                sampled_at="2026-07-09T22:00:00+00:00",
                sample_times=(
                    "2026-07-09T18:00:00+00:00",
                    "2026-07-09T21:00:00+00:00",
                    "2026-07-09T22:00:00+00:00",
                    "2026-07-10T02:00:00+00:00",
                ),
            )
        )
        before = deepcopy(home_target)

        controller._refresh_nsom_diagnostics()
        exported = controller._export_nsom_diagnostics()

        json.dumps(exported, allow_nan=False)
        self.assertEqual(home_target, before)
        self.assertEqual(controller._nsom_diagnostic_snapshot.confidence.moon_geometry_confidence, 1.0)
        confidence_inputs = dict(controller._nsom_diagnostic_snapshot.confidence_inputs)
        self.assertTrue(confidence_inputs["moon_geometry_available"])
        home_export = next(target for target in exported["targets"] if target["source"] == "home")
        home_runtime_fields = dict(home_export["runtimeFields"])
        self.assertTrue(home_runtime_fields["moon_geometry_available"])
        self.assertEqual(home_runtime_fields["moon_altitude_deg"], 41.5)
        self.assertEqual(home_runtime_fields["moon_target_separation_deg"], 72.25)
        self.assertEqual(home_runtime_fields["moon_above_horizon"], True)
        self.assertEqual(home_runtime_fields["moon_visible_during_target_window"], True)
        self.assertEqual(home_runtime_fields["moon_set_before_target_window"], False)
        self.assertEqual(home_runtime_fields["moon_geometry_score_effect"], 0.0)
        self.assertEqual(home_export["runtimeFields"]["score"], 82)
        self.assertEqual(home_export["observableTargetValue"]["value"], 82.0)
        self.assertEqual(controller._astronomy_engine.calls, 1)

    def test_refresh_nsom_diagnostics_reuses_planner_moon_geometry_cache(self) -> None:
        home_target = _object("messier-M13", "M13", "Ammasso globulare", 82)
        controller = _controller(
            [home_target],
            [_plan_item("messier-M13", "M13", score=82)],
            best_object=home_target,
        )
        controller._night_planner_service = NightPlannerService()
        controller._astronomy_engine = _MoonGeometryEngine(
            MoonGeometrySummary(
                object_id="messier-M13",
                moon_altitude_deg=41.5,
                moon_target_separation_deg=72.25,
                moon_above_horizon=True,
                moon_visible_during_target_window=True,
                moon_set_before_target_window=False,
            )
        )

        planner_geometry = controller._planner_moon_geometry_inputs([home_target])
        controller._refresh_nsom_diagnostics()

        self.assertIsNotNone(planner_geometry)
        self.assertEqual(controller._astronomy_engine.calls, 1)
        self.assertEqual(
            controller._moon_geometry_condition_cache[home_target.id].moon_target_separation_deg,
            72.25,
        )

    def test_export_nsom_diagnostics_is_strict_json_compatible(self) -> None:
        home_target = _object("messier-M13", "M13", "Ammasso globulare", 82)
        plan_item = _plan_item("messier-M13", "M13", score=float("nan"))
        controller = _controller([home_target], [plan_item], best_object=home_target)
        controller._refresh_nsom_diagnostics()

        exported = controller._export_nsom_diagnostics()

        json.dumps(exported, allow_nan=False)
        planner_target = exported["planner"]["targets"][0]
        self.assertIsNone(planner_target["runtimeFields"]["score"])

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

    def test_export_nsom_diagnostics_is_side_effect_free(self) -> None:
        target = _object("messier-M13", "M13", "Ammasso globulare", 82)
        controller = _controller([target], [_plan_item("messier-M13", "M13", score=82)], best_object=target)
        controller._refresh_nsom_diagnostics()
        controller._refresh_nsom_diagnostics = Mock(side_effect=AssertionError("no refresh"))
        for method_name in (
            "_recalculate_observing_outputs",
            "_refresh_equipment_recommendations_for_current_objects",
            "_refresh_sky_compass",
            "_refresh_sky_compass_live",
            "_start_weather_refresh",
        ):
            setattr(controller, method_name, Mock(side_effect=AssertionError(method_name)))
        signal_slots = []
        for signal in (
            controller.dataChanged,
            controller.weatherChanged,
            controller.selectedObjectChanged,
            controller.equipmentChanged,
            controller.skyCompassChanged,
            controller.statusChanged,
        ):
            slot = Mock()
            signal.connect(slot)
            signal_slots.append(slot)

        with (
            patch("astro_viewer.app.viewmodels.app_controller.logger.debug", side_effect=AssertionError("no logging")),
            patch("astro_viewer.app.viewmodels.app_controller.logger.info", side_effect=AssertionError("no logging")),
            patch("astro_viewer.app.viewmodels.app_controller.logger.warning", side_effect=AssertionError("no logging")),
            patch("pathlib.Path.write_text", side_effect=AssertionError("no file writes")),
        ):
            exported = controller._export_nsom_diagnostics()

        self.assertEqual(exported["metadata"]["schema"], "nsom_diagnostic_snapshot")
        controller._refresh_nsom_diagnostics.assert_not_called()
        for slot in signal_slots:
            slot.assert_not_called()

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
            source.index("self._refresh_sky_compass()"),
            source.index("self._refresh_nsom_diagnostics()"),
        )

    def test_provider_completion_refreshes_snapshot_without_observing_recompute(self) -> None:
        controller = _controller([], [])
        controller._refresh_nsom_diagnostics = Mock()
        controller._mark_refresh_dirty = Mock()
        controller._clear_refresh_domains = Mock()
        controller._recalculate_observing_outputs = Mock(side_effect=AssertionError("no observing recompute"))
        controller._refresh_equipment_recommendations_for_current_objects = Mock(
            side_effect=AssertionError("no equipment recompute")
        )
        controller._refresh_sky_compass = Mock(side_effect=AssertionError("no compass recompute"))
        controller._night_planner_service = Mock()
        controller._openaq_credential_store = Mock()
        controller._openaq_credential_store.api_key.return_value = "openaq-secret"
        controller._openaq_credentials_state = Mock(connection_verified=True)
        location_key = LightPollutionService._location_key(controller._location)

        controller._finish_local_atmosphere_refresh(location_key, LocalAtmosphere.no_data())

        controller._refresh_nsom_diagnostics.assert_called_once()
        controller._recalculate_observing_outputs.assert_not_called()
        controller._night_planner_service.plan.assert_not_called()

        controller._refresh_nsom_diagnostics.reset_mock()
        controller._earthdata_credentials_state = Mock(connection_verified=True)
        controller._log_nasa_aod_result = Mock()

        controller._finish_nasa_aod_refresh(location_key, NasaAodResult.no_location())

        controller._refresh_nsom_diagnostics.assert_called_once()
        controller._recalculate_observing_outputs.assert_not_called()
        controller._night_planner_service.plan.assert_not_called()


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
    controller._moon_geometry_condition_cache = {}
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


def _plan_item(object_id: str, name: str, *, score: int | float) -> NightPlanItem:
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


class _MoonGeometryEngine:
    def __init__(self, summary: MoonGeometrySummary | None) -> None:
        self._summary = summary
        self.calls = 0

    def moon_geometry(
        self,
        location: ObserverLocation,
        target: CelestialObject,
    ) -> MoonGeometrySummary | None:
        del location, target
        self.calls += 1
        return self._summary


if __name__ == "__main__":
    unittest.main()
