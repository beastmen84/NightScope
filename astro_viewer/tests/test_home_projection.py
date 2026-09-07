"""Compare the lean Home contract with the pre-optimization rich projection."""

from collections import Counter
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
from PIL import Image
from PySide6.QtCore import QCoreApplication, QObject

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.services.home_night_plan_overview import HomeNightPlanOverviewService
from astro_viewer.app.services.localization import render_payload, tr
from astro_viewer.app.services.personal_images import prepare_image
from astro_viewer.app.services.translation_manager import TranslationManager
from astro_viewer.app.viewmodels.app_controller import AppController, bortle_observing_warning
from astro_viewer.tests.test_home_night_plan_overview import _session, _setup_model
from astro_viewer.tests.test_home_night_target_pool import _plan_item, _target
from astro_viewer.tests.test_phase6_real_data import _controller


BASE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def home_controller():
    # Keep geometry/ranking out of this presentation boundary test. The real
    # target-pool, image, clock, sorting and final read-model code still run.
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._base_dir = BASE_DIR
    controller._location = None
    controller._sky_quality = None
    controller._moon = None
    controller._is_loading = False
    controller._object_descriptions = {}
    controller._object_image_map = {}
    controller._catalogue_identifier_index = {}
    controller._catalogue_month_visible_for_object = lambda _object_id: None
    controller._home_night_plan_overview_service = HomeNightPlanOverviewService()
    controller._test_session = _session("recommended")
    controller._home_observing_overview_payload = lambda: {"session": controller._test_session}
    controller._active_profile_payload = lambda: {"profile_name": "Home fixture"}
    controller._test_assigned = [{"kind": "telescope", "id": "scope"}]
    controller._profile_assigned_equipment = lambda: controller._test_assigned
    start = datetime(2026, 9, 7, 19, tzinfo=ZoneInfo("Europe/Rome"))
    controller._observing_night_window = ObservingNightWindow.bounded(start, start + timedelta(hours=12))
    targets = [
        _target("jupiter", "Giove", "Pianeta", "04:00", 90),
        _target("moon", "Luna", "Luna", "22:00", 85),
        *[_target(f"ngc-{i}", f"NGC {i}", "Galaxy", "23:30" if i % 2 else "01:30", 75)
          for i in (100, 40, 3, 20, 2, 8, *range(101, 125))],
    ]
    controller._visible_planets = targets[:1]
    controller._test_deep_sky = [*targets[1:], replace(targets[0], id=" JUPITER ", name="duplicate")]
    controller._conditioned_deep_sky_candidates = lambda: controller._test_deep_sky
    controller._night_plan = [_plan_item(item) for item in targets[:6]]
    controller._night_plan.insert(1, controller._night_plan[0])
    controller._equipment_setup_read_models_by_object_id = {
        item.id: replace(_setup_model(), object_id=item.id, requires_optical_instrument=i % 2 == 0)
        for i, item in enumerate(targets)
        if i != len(targets) - 1  # A missing setup must stay excluded for naked eye.
    }
    return controller


def legacy_overview(controller):
    """Freeze the 1.46.20 assembly, retaining the full public detail projection."""
    pool = controller._tonight_target_pool()
    return render_payload(controller._home_night_plan_overview_service.build(
        session=controller._home_observing_overview_payload().get("session", {}),
        night_plan=controller._night_plan,
        target_payloads_by_id={item.id: controller._object_to_qml(item) for item in pool},
        setup_models_by_object_id=controller._equipment_setup_read_models_by_object_id,
        alternatives=controller._home_visible_alternative_payloads(pool),
        active_profile=controller._active_profile_payload(),
        assigned_equipment=controller._profile_assigned_equipment(),
        loading=controller._is_loading,
        sky_quality_warning=(
            bortle_observing_warning(controller._sky_quality.bortle_class)
            if controller._sky_quality
            else tr("Inquinamento luminoso non disponibile: visibilità locale da verificare.")
            if controller._has_valid_location() else ""
        ),
    ))


@pytest.mark.parametrize("state", ["recommended", "monitor", "discouraged", "pending", "unavailable", "unknown"])
@pytest.mark.parametrize("loading", [False, True])
@pytest.mark.parametrize("kinds", [[], ["telescope"], ["binocular"], ["telescope", "telescope", "eyepiece", "barlow"]])
def test_home_projection_preserves_every_field_for_session_and_profile(home_controller, state, loading, kinds):
    controller = home_controller
    controller._test_session = _session(state)
    controller._is_loading = loading
    controller._test_assigned = [{"kind": kind, "id": str(i)} for i, kind in enumerate(kinds)]
    if controller._test_assigned:
        controller._test_assigned.append(dict(controller._test_assigned[0]))
    actual = controller.homeNightPlanOverview
    assert actual == legacy_overview(controller)
    assert len(actual["plan"]["items"]) == (4 if state == "recommended" else 0)
    assert actual["alternatives"]["totalCount"] > 10


@pytest.mark.parametrize("night", [None, "unavailable", "no_night", "continuous", "ordinary", "spring_dst", "autumn_dst"])
def test_home_projection_preserves_midnight_dst_and_legacy_clock_fallbacks(home_controller, night):
    controller = home_controller
    if night is None:
        del controller._observing_night_window
    elif night == "unavailable":
        controller._observing_night_window = ObservingNightWindow.unavailable()
    elif night == "no_night":
        controller._observing_night_window = ObservingNightWindow.no_night()
    elif night == "continuous":
        controller._observing_night_window = ObservingNightWindow.continuous_night(
            datetime(2026, 12, 7, tzinfo=ZoneInfo("Europe/Oslo")),
        )
    else:
        month, day = {"ordinary": (9, 7), "spring_dst": (3, 28), "autumn_dst": (10, 24)}[night]
        start = datetime(2026, month, day, 19, tzinfo=ZoneInfo("Europe/Rome"))
        controller._observing_night_window = ObservingNightWindow.bounded(start, start + timedelta(hours=12))
    controller._night_plan = []
    controller._test_deep_sky = [
        replace(item, best_time=best, observing_window=window,
                observing_start_at=begin, observing_end_at=end, best_observing_at=peak)
        for item, (best, window, begin, end, peak) in zip(controller._test_deep_sky, [
            ("23:30", "22:00 - 01:00", "", "", ""),
            ("01:30", "00:15 - 03:00", "", "", ""),
            ("", "", "", "", ""),
            ("invalid", "outside", "invalid", "invalid", "invalid"),
            ("23:30", "22:00 - 01:00", "2026-09-07T22:00:00+02:00", "2026-09-08T01:00:00+02:00", "2026-09-08T00:00:00+02:00"),
            ("02:30", "02:10 - 03:00", "2026-10-25T02:10:00+02:00", "2026-10-25T03:00:00+01:00", "2026-10-25T02:30:00+01:00"),
        ])
    ]
    assert controller.homeNightPlanOverview == legacy_overview(controller)


@pytest.mark.parametrize("language", ["it", "en", "es"])
def test_home_projection_preserves_translated_contract(home_controller, tmp_path, language):
    app = QCoreApplication.instance() or QCoreApplication([])
    translation = TranslationManager(BASE_DIR / "translations", tmp_path / "preferences.json")
    assert translation.install()
    try:
        home_controller.homeNightPlanOverview
        timing = home_controller._home_target_timing
        assert translation.setLanguage(language)
        assert home_controller.homeNightPlanOverview == legacy_overview(home_controller)
        assert home_controller._home_target_timing is timing
    finally:
        translation.setLanguage("it")
        app.removeTranslator(translation._translator)


def test_home_projection_has_no_full_detail_work_or_duplicate_conversions(home_controller, monkeypatch):
    controller = home_controller
    expected = legacy_overview(controller)
    # A full setup DTO (including nested lists), descriptions, status and detail
    # geometry must never be prepared just to display the compact Home rows.
    monkeypatch.setattr(controller, "_object_to_qml", Mock(side_effect=AssertionError("rich projection")))
    counts = Counter()
    original = controller._home_target_to_qml

    def project(item, **kwargs):
        counts[item.id] += 1
        return original(item, **kwargs)

    monkeypatch.setattr(controller, "_home_target_to_qml", project)
    assert controller.homeNightPlanOverview == expected
    assert counts == Counter({item.id: 1 for item in controller._tonight_target_pool()})


def test_home_projection_does_not_cache_stale_or_mutable_payloads(home_controller):
    controller = home_controller
    first = controller.homeNightPlanOverview
    first["alternatives"]["items"].clear()
    controller._test_deep_sky = [replace(item, name=item.name + " changed", direction="Ovest")
                                 for item in controller._test_deep_sky]
    controller._test_session = _session("monitor")
    controller._night_plan = []
    assert controller.homeNightPlanOverview == legacy_overview(controller)
    assert controller.homeNightPlanOverview["alternatives"]["items"]


def test_home_projection_preserves_orphan_plan_and_image_type_override(home_controller):
    controller = home_controller
    orphan = _target("absent", "Absent", "Galaxy", "22:00", 90)
    controller._night_plan = [replace(_plan_item(orphan), image="orphan.jpg")]
    controller._catalogue_identifier_index["ngc-100"] = {"type": "Open cluster"}
    controller._object_image_map["ngc-40"] = {"image_path": "file:///custom.jpg", "thumbnail_path": "file:///thumb.jpg"}
    actual = controller.homeNightPlanOverview
    assert actual == legacy_overview(controller)
    assert actual["plan"]["items"][0]["image"] == "orphan.jpg"
    assert actual["plan"]["items"][0]["defaultImage"] == ""


def test_home_projection_rechecks_personal_images_and_fallback_without_notifications(home_controller, tmp_path):
    controller = home_controller
    with _controller() as real_controller:
        controller._personal_image_service = real_controller._personal_image_service
        service = controller._personal_image_service
        source = tmp_path / "personal image à.png"
        Image.new("RGB", (32, 16), "orange").save(source)
        prepared = prepare_image(source)
        controller._night_plan = []

        def image_row():
            actual = controller.homeNightPlanOverview
            assert actual == legacy_overview(controller)
            return next(row for row in actual["alternatives"]["items"] if row["objectId"] == "jupiter")

        default = image_row()
        service.save("jupiter", prepared)
        full_path, thumb_path = service.paths(prepared.digest)
        assert image_row()["image"] == thumb_path.resolve().as_uri()
        assert image_row()["defaultImage"] == default["defaultImage"]
        thumb_path.unlink()
        assert image_row()["image"] == full_path.resolve().as_uri()
        full_path.unlink()
        assert image_row() == default
        assert controller._object_to_qml(controller._visible_planets[0])["personalImageMissing"]
        service.save("jupiter", prepared)
        assert image_row()["image"] == thumb_path.resolve().as_uri()
        service.reset("jupiter")
        assert image_row() == default
