from __future__ import annotations

import unittest

from astro_viewer.app.services.refresh_lifecycle import (
    RefreshDomain,
    RefreshManager,
    RefreshReason,
)


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

        self.assertEqual(affected, frozenset({RefreshDomain.COMPASS}))
        self.assertTrue(manager.is_dirty(RefreshDomain.COMPASS))
        self.assertFalse(manager.is_dirty(RefreshDomain.PLANNER))

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
        self.assertIn(RefreshDomain.PLANNER, affected)
        self.assertFalse(RefreshDomain.LOCATION in affected)
        self.assertFalse(RefreshDomain.ASTRONOMY in affected)


if __name__ == "__main__":
    unittest.main()
