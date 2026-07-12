from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QObject

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.earthdata_credentials import EarthdataCredentialState
from astro_viewer.app.services.light_pollution_service import ViirsCacheState
from astro_viewer.app.services.refresh_lifecycle import (
    RefreshDomain,
    RefreshManager,
    RefreshReason,
)
from astro_viewer.app.viewmodels.app_controller import AppController


class RefreshManagerTest(unittest.TestCase):
    def test_location_changed_marks_location_dependent_domains(self) -> None:
        manager = RefreshManager()

        affected = manager.mark_dirty(RefreshReason.LOCATION_CHANGED)

        self.assertIn(RefreshDomain.ASTRONOMY, affected)
        self.assertIn(RefreshDomain.WEATHER, affected)
        self.assertIn(RefreshDomain.SKY_QUALITY, affected)
        self.assertIn(RefreshDomain.AIR_QUALITY, affected)
        self.assertIn(RefreshDomain.AOD, affected)
        self.assertIn(RefreshDomain.PLANNER, affected)
        self.assertIn(RefreshDomain.COMPASS, affected)
        self.assertTrue(manager.is_dirty(RefreshDomain.CATALOG))

    def test_equipment_changed_keeps_unrelated_domains_clean(self) -> None:
        manager = RefreshManager()

        affected = manager.mark_dirty(RefreshReason.EQUIPMENT_CHANGED)

        self.assertEqual(
            affected,
            frozenset(
                {
                    RefreshDomain.EQUIPMENT,
                    RefreshDomain.PLANNER,
                    RefreshDomain.COMPASS,
                }
            ),
        )
        self.assertFalse(manager.is_dirty(RefreshDomain.WEATHER))
        self.assertFalse(manager.is_dirty(RefreshDomain.AIR_QUALITY))
        self.assertFalse(manager.is_dirty(RefreshDomain.AOD))

    def test_live_tick_is_reserved_for_compass_only(self) -> None:
        manager = RefreshManager()

        affected = manager.mark_dirty(RefreshReason.LIVE_TICK)

        self.assertEqual(affected, frozenset({RefreshDomain.COMPASS_LIVE}))
        self.assertTrue(manager.is_dirty(RefreshDomain.COMPASS_LIVE))
        self.assertFalse(manager.is_dirty(RefreshDomain.COMPASS))
        self.assertFalse(manager.is_dirty(RefreshDomain.PLANNER))

    def test_generic_ttl_expired_does_not_dirty_unrelated_domains(self) -> None:
        manager = RefreshManager()

        affected = manager.mark_dirty(RefreshReason.TTL_EXPIRED)

        self.assertEqual(affected, frozenset())
        self.assertEqual(manager.snapshot(), frozenset())

    def test_domain_specific_ttl_mappings_are_not_over_broad(self) -> None:
        manager = RefreshManager()

        weather = manager.domains_for_reason(RefreshReason.WEATHER_TTL_EXPIRED)
        air_quality = manager.domains_for_reason(RefreshReason.AIR_QUALITY_TTL_EXPIRED)
        aod = manager.domains_for_reason(RefreshReason.AOD_TTL_EXPIRED)

        self.assertEqual(
            weather,
            frozenset(
                {
                    RefreshDomain.WEATHER,
                    RefreshDomain.EQUIPMENT,
                    RefreshDomain.PLANNER,
                    RefreshDomain.COMPASS,
                }
            ),
        )
        self.assertEqual(air_quality, frozenset({RefreshDomain.AIR_QUALITY}))
        self.assertEqual(aod, frozenset({RefreshDomain.AOD}))
        self.assertNotIn(RefreshDomain.PLANNER, air_quality)
        self.assertNotIn(RefreshDomain.COMPASS, aod)

    def test_generic_async_completed_does_not_dirty_unrelated_domains(self) -> None:
        manager = RefreshManager()

        affected = manager.mark_dirty(RefreshReason.ASYNC_COMPLETED)

        self.assertEqual(affected, frozenset())
        self.assertEqual(manager.snapshot(), frozenset())

    def test_domain_specific_completion_mappings_match_current_behaviour(self) -> None:
        manager = RefreshManager()

        weather = manager.domains_for_reason(RefreshReason.WEATHER_COMPLETED)
        air_quality = manager.domains_for_reason(RefreshReason.AIR_QUALITY_COMPLETED)
        aod = manager.domains_for_reason(RefreshReason.AOD_COMPLETED)
        sky_quality = manager.domains_for_reason(RefreshReason.SKY_QUALITY_COMPLETED)

        self.assertIn(RefreshDomain.EQUIPMENT, weather)
        self.assertIn(RefreshDomain.PLANNER, weather)
        self.assertIn(RefreshDomain.COMPASS, weather)
        self.assertEqual(air_quality, frozenset({RefreshDomain.AIR_QUALITY}))
        self.assertEqual(aod, frozenset({RefreshDomain.AOD}))
        self.assertEqual(
            sky_quality,
            frozenset(
                {
                    RefreshDomain.SKY_QUALITY,
                    RefreshDomain.EQUIPMENT,
                    RefreshDomain.PLANNER,
                    RefreshDomain.COMPASS,
                }
            ),
        )

    def test_clear_domains_removes_only_selected_dirty_domains(self) -> None:
        manager = RefreshManager()
        manager.mark_dirty(RefreshReason.LOCATION_CHANGED)

        manager.clear_domains((RefreshDomain.WEATHER, RefreshDomain.AOD))

        self.assertFalse(manager.is_dirty(RefreshDomain.WEATHER))
        self.assertFalse(manager.is_dirty(RefreshDomain.AOD))
        self.assertTrue(manager.is_dirty(RefreshDomain.ASTRONOMY))
        self.assertTrue(manager.is_dirty(RefreshDomain.COMPASS))

    def test_clear_all_removes_all_dirty_domains(self) -> None:
        manager = RefreshManager()
        manager.mark_dirty(RefreshReason.LOCATION_CHANGED)

        manager.clear_all()

        self.assertEqual(manager.snapshot(), frozenset())

    def test_explicit_domains_override_reason_mapping(self) -> None:
        manager = RefreshManager()

        affected = manager.mark_dirty(
            RefreshReason.MANUAL,
            (RefreshDomain.WEATHER,),
        )

        self.assertEqual(affected, frozenset({RefreshDomain.WEATHER}))
        self.assertTrue(manager.is_dirty(RefreshDomain.WEATHER))
        self.assertFalse(manager.is_dirty(RefreshDomain.AOD))
        self.assertEqual(manager.last_reason, RefreshReason.MANUAL)

    def test_api_key_changed_maps_only_provider_dependent_domains(self) -> None:
        manager = RefreshManager()

        affected = manager.domains_for_reason(RefreshReason.API_KEY_CHANGED)

        self.assertIn(RefreshDomain.SKY_QUALITY, affected)
        self.assertIn(RefreshDomain.AIR_QUALITY, affected)
        self.assertIn(RefreshDomain.AOD, affected)
        self.assertNotIn(RefreshDomain.PLANNER, affected)
        self.assertNotIn(RefreshDomain.COMPASS, affected)
        self.assertFalse(RefreshDomain.LOCATION in affected)
        self.assertFalse(RefreshDomain.ASTRONOMY in affected)

    def test_last_reason_is_diagnostic_while_domain_reasons_are_operational(self) -> None:
        manager = RefreshManager()

        manager.mark_dirty(RefreshReason.WEATHER_TTL_EXPIRED)
        manager.mark_dirty(RefreshReason.AOD_TTL_EXPIRED)

        self.assertEqual(manager.last_reason, RefreshReason.AOD_TTL_EXPIRED)
        self.assertEqual(
            manager.reason_for_domain(RefreshDomain.WEATHER),
            RefreshReason.WEATHER_TTL_EXPIRED,
        )
        self.assertEqual(
            manager.reason_for_domain(RefreshDomain.AOD),
            RefreshReason.AOD_TTL_EXPIRED,
        )

    def test_viirs_scheduling_leaves_sky_quality_dirty_until_completion(self) -> None:
        controller = AppController.__new__(AppController)
        QObject.__init__(controller)
        controller._location = ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")
        controller._earthdata_credentials_state = EarthdataCredentialState(
            username="earth-user",
            configured=True,
            secure_store_available=True,
            connection_verified=True,
        )
        controller._viirs_sky_quality_running = False
        controller._sky_quality = None
        controller._light_pollution_status = ""
        controller._light_pollution_service = Mock()
        controller._light_pollution_service.viirs_cache_state.return_value = ViirsCacheState.MISSING
        controller._refresh_manager = RefreshManager()
        controller._astronomy_engine = _FakeAstronomyEngine()
        controller._refresh_equipment_recommendations_for_current_objects = lambda: None
        controller._apply_deep_sky_pollution_context = lambda objects: objects
        controller._recalculate_observing_outputs = lambda: None
        controller._seeing_service = Mock()
        controller._observing_weather_hours = Mock(return_value=[])
        controller._start_astronomy_refresh = Mock(return_value=False)
        controller._deep_sky = []

        with patch("astro_viewer.app.viewmodels.app_controller.Thread") as thread_cls:
            controller._schedule_viirs_sky_quality_refresh()

        thread_cls.assert_called_once()
        thread_cls.return_value.start.assert_called_once()
        self.assertTrue(controller._refresh_manager.is_dirty(RefreshDomain.SKY_QUALITY))
        self.assertEqual(
            controller._refresh_manager.reason_for_domain(RefreshDomain.SKY_QUALITY),
            RefreshReason.SKY_QUALITY_TTL_EXPIRED,
        )

        controller._finish_viirs_sky_quality_refresh(
            "9.030:38.740:addis ababa",
            SkyQuality(4, 21.0, 0.1, "NASA Black Marble VNP46A3", "VIIRS", "ok"),
            "Dati VIIRS NASA aggiornati.",
        )

        controller._seeing_service.estimate.assert_called_once_with([], controller._sky_quality)
        self.assertFalse(controller._refresh_manager.is_dirty(RefreshDomain.SKY_QUALITY))

    def test_fresh_viirs_cache_skips_background_lookup(self) -> None:
        controller = AppController.__new__(AppController)
        QObject.__init__(controller)
        controller._location = ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")
        controller._earthdata_credentials_state = EarthdataCredentialState(
            username="earth-user",
            configured=True,
            secure_store_available=True,
            connection_verified=True,
        )
        controller._viirs_sky_quality_running = False
        controller._light_pollution_status = "old status"
        controller._light_pollution_service = Mock()
        controller._light_pollution_service.viirs_cache_state.return_value = ViirsCacheState.FRESH
        controller._refresh_manager = RefreshManager()

        with patch("astro_viewer.app.viewmodels.app_controller.Thread") as thread_cls:
            controller._schedule_viirs_sky_quality_refresh()

        thread_cls.assert_not_called()
        self.assertFalse(controller._viirs_sky_quality_running)
        self.assertEqual(controller._light_pollution_status, "")
        self.assertFalse(controller._refresh_manager.is_dirty(RefreshDomain.SKY_QUALITY))

    def test_stale_viirs_refresh_failure_reports_cached_fallback(self) -> None:
        controller = AppController.__new__(AppController)
        QObject.__init__(controller)
        controller._location = ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")
        controller._earthdata_credentials_state = EarthdataCredentialState(
            username="earth-user",
            configured=True,
            secure_store_available=True,
            connection_verified=True,
        )
        controller._viirs_sky_quality_running = False
        controller._light_pollution_status = ""
        controller._light_pollution_service = Mock()
        controller._light_pollution_service.viirs_cache_state.return_value = ViirsCacheState.STALE
        controller._light_pollution_service.remote_sky_quality.return_value = None
        controller._refresh_manager = RefreshManager()
        emissions: list[tuple[str, object, str]] = []
        controller._viirsSkyQualityFinished.connect(
            lambda location_key, quality, message: emissions.append((location_key, quality, message))
        )

        with patch("astro_viewer.app.viewmodels.app_controller.Thread") as thread_cls:
            controller._schedule_viirs_sky_quality_refresh()
            run_lookup = thread_cls.call_args.kwargs["target"]
            run_lookup()

        self.assertEqual(controller._light_pollution_status, "Verifica aggiornamenti VIIRS NASA...")
        self.assertEqual(
            emissions,
            [
                (
                    "9.030:38.740:addis ababa",
                    None,
                    "Aggiornamento VIIRS non disponibile; uso dati in cache.",
                )
            ],
        )


class _FakeAstronomyEngine:
    def recommended_deep_sky(self, _location) -> list:
        return []


if __name__ == "__main__":
    unittest.main()
