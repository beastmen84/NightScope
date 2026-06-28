from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.services.sky_compass_service import SkyCompassService


APP_CONTROLLER = Path(__file__).resolve().parents[1] / "app" / "viewmodels" / "app_controller.py"
HOME_PAGE = Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "HomePage.qml"


def test_sky_compass_ranks_broad_direction_from_home_targets() -> None:
    service = SkyCompassService()
    m13 = _object("messier-M13", "M13", "Ammasso globulare", "Nord-Est", 72)
    m92 = _object("messier-M92", "M92", "Ammasso globulare", "Nord-Est", 58)
    venus = _object("venus", "Venere", "Pianeta", "Est", 94)
    plan = [_plan_item(m13)]

    result = service.compass([venus, m92, m13], plan, m13, has_location=True)

    assert result["available"] is True
    assert result["direction"] == "Nord-Est"
    assert result["targetCount"] == 2
    assert result["targets"][0]["id"] == "messier-M13"
    assert result["targetNames"] == "M13 · M92"
    assert result["alternatives"][0]["direction"] == "Est"


def test_sky_compass_skips_targets_without_current_direction() -> None:
    service = SkyCompassService()

    result = service.compass(
        [
            _object("messier-M13", "M13", "Ammasso globulare", "n/d", 80),
            _object("messier-M92", "M92", "Ammasso globulare", "Ovest", 60),
        ],
        [],
        None,
        has_location=True,
    )

    assert result["available"] is True
    assert result["direction"] == "Ovest"
    assert result["targetNames"] == "M92"


def test_sky_compass_no_location_fallback() -> None:
    service = SkyCompassService()

    result = service.compass([_object("mars", "Marte", "Pianeta", "Sud", 80)], [], None, has_location=False)

    assert result["available"] is False
    assert result["reason"] == "no_location"
    assert "località" in result["message"]


def test_sky_compass_direction_buckets_are_eight_sector() -> None:
    service = SkyCompassService()

    assert service.normalize_direction("Nord-Est") == "Nord-Est"
    assert service.normalize_direction("Sud-Est") == "Sud-Est"
    assert service.normalize_direction("Sud-Ovest") == "Sud-Ovest"
    assert service.normalize_direction("Nord-Ovest") == "Nord-Ovest"
    assert service.normalize_direction("Nord") == "Nord"
    assert service.normalize_direction("Est") == "Est"
    assert service.normalize_direction("Sud") == "Sud"
    assert service.normalize_direction("Ovest") == "Ovest"


def test_sky_compass_uses_home_filtered_planets_not_raw_solar_system_objects() -> None:
    body = _python_function_body("_sky_compass_candidates")

    assert "_home_visible_objects(self._visible_planets)" in body
    assert "_solar_system_objects" not in body


def test_home_renders_sky_compass_below_sky_map_without_timer() -> None:
    source = HOME_PAGE.read_text(encoding="utf-8")

    assert source.index('title: "Mappa cielo"') < source.index('title: "Sky Compass"')
    assert source.index('title: "Sky Compass"') < source.index('title: "Prossimi eventi"')
    assert "Timer {" not in source


def _object(object_id: str, name: str, object_type: str, direction: str, score: int) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="",
        distance="",
        max_altitude="45 gradi",
        direction=direction,
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        difficulty="Media",
    )


def _plan_item(item: CelestialObject) -> NightPlanItem:
    return NightPlanItem(
        time_label="22:00 sera",
        object_id=item.id,
        name=item.name,
        score=item.score,
        difficulty=item.difficulty,
        setup=item.recommended_setup,
        direction=item.direction,
        image=item.image,
    )


def _python_function_body(name: str) -> str:
    source = APP_CONTROLLER.read_text(encoding="utf-8")
    marker = f"def {name}"
    start = source.index(marker)
    next_def = source.find("\n    def ", start + len(marker))
    if next_def == -1:
        return source[start:]
    return source[start:next_def]
