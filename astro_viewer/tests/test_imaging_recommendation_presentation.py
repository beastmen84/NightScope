"""Protect localized photographic recommendation payloads and capture guidance."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

from astro_viewer.app.models.equipment import Barlow, FocalReducer, Telescope
from astro_viewer.app.models.imaging import ImagingCamera, ImagingCameraKind
from astro_viewer.app.models.imaging_exposure import ImagingSessionConditions
from astro_viewer.app.models.imaging_runtime import (
    ImagingRuntimeConditions,
    ImagingRuntimeInventory,
    ImagingRuntimeStatus,
)
from astro_viewer.app.models.imaging_video_capture import (
    ImagingVideoSessionConditions,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import SeeingTransparency
from astro_viewer.app.services.imaging_recommendation_presentation import (
    ImagingRecommendationPresenter,
)
from astro_viewer.app.services.imaging_runtime_assembler import (
    ImagingRuntimeAssembler,
)
from astro_viewer.app.services.localization import render_payload
from astro_viewer.app.viewmodels.app_controller import AppController


def _target(
    target_id: str = "messier-M31",
    *,
    name: str = "M31 Andromeda Galaxy",
    object_type: str = "Galaxy",
    magnitude: str = "3.4",
    apparent_size: str = "3.17° × 1°",
    max_size_deg: float | None = 3.17,
    altitude_deg: float | None = 52.0,
    max_altitude: str = "60°",
) -> CelestialObject:
    return CelestialObject(
        id=target_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude=max_altitude,
        direction="",
        best_time="",
        observing_window="",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="",
        apparent_size=apparent_size,
        max_angular_size_deg=max_size_deg,
        current_altitude_degrees=altitude_deg,
    )


def _telescope() -> Telescope:
    return Telescope(
        id="scope",
        name="Celestron NexStar 6SE",
        aperture_mm=150,
        focal_length_mm=1500,
        optical_type="Schmidt-Cassegrain",
        mount="ALTAZ_GOTO",
    )


def _camera() -> ImagingCamera:
    return ImagingCamera(
        id="camera",
        name="SVBONY SV705C",
        kind=ImagingCameraKind.ASTRONOMY_CAMERA,
        sensor_width_mm=11.2,
        sensor_height_mm=6.3,
        resolution_width_px=3856,
        resolution_height_px=2180,
        pixel_size_um=2.9,
        bit_depth=12,
        camera_class="ALL_ROUND",
        sensor_technology="CMOS",
        color_mode="COLOR",
        full_resolution_fps=45.0,
        cooled=False,
        shutter_type="ROLLING",
        backfocus_mm=6.5,
    )


def _inventory() -> ImagingRuntimeInventory:
    telescope = _telescope()
    return ImagingRuntimeInventory(
        profile_id="1",
        telescopes=(telescope,),
        cameras=(_camera(),),
        reducers=(
            FocalReducer(
                id="reducer",
                name="Celestron Reducer-Corrector f/6.3",
                reduction_factor=0.63,
                optical_system="SCHMIDT_CASSEGRAIN",
                backfocus_mm=105.0,
                imaging_compatible=True,
                compatible_telescope_ids=(telescope.id,),
            ),
        ),
        barlows=(
            Barlow(
                id="barlow",
                name="Celestron X-Cel LX 2x Barlow Lens 2x",
                multiplier=2.0,
            ),
        ),
    )


def _conditions(
    *,
    altitude_deg: float = 52.0,
    maximum_altitude_deg: float = 60.0,
    transparency_score: int = 75,
) -> ImagingRuntimeConditions:
    return ImagingRuntimeConditions(
        still=ImagingSessionConditions(
            sky_brightness_mag_arcsec2=20.5,
            bortle_class=5,
            transparency_score=transparency_score,
            target_current_altitude_deg=altitude_deg,
            target_maximum_altitude_deg=maximum_altitude_deg,
            moon_illumination_fraction=0.2,
            moon_altitude_deg=-5,
            moon_target_separation_deg=90,
            moon_visible_during_target_window=False,
        ),
        video=ImagingVideoSessionConditions(
            seeing_score=80,
            target_altitude_deg=altitude_deg,
        ),
    )


def _presented(
    target: CelestialObject,
    *,
    altitude_deg: float = 52.0,
    maximum_altitude_deg: float = 60.0,
    transparency_score: int = 75,
) -> dict[str, object]:
    recommendation = ImagingRuntimeAssembler().assemble(
        target,
        _inventory(),
        _conditions(
            altitude_deg=altitude_deg,
            maximum_altitude_deg=maximum_altitude_deg,
            transparency_score=transparency_score,
        ),
    )
    presentation = ImagingRecommendationPresenter().present(
        recommendation
    )
    return render_payload(presentation.to_payload())


def test_still_presentation_exposes_plan_geometry_and_real_profile_limits() -> None:
    payload = _presented(_target())

    assert payload["ready"] is True
    assert payload["modeCode"] == "still"
    assert payload["modeLabel"] == "Foto a lunga posa"
    assert payload["modifierLabel"] == "Riduttore di focale 0,63×"
    assert payload["setupText"] == (
        "Celestron NexStar 6SE + Celestron Reducer-Corrector f/6.3 "
        "+ SVBONY SV705C"
    )
    assert payload["mechanicalText"] == (
        "Backfocus richiesto: 105 mm · spaziatura ottica residua stimata: "
        "98,5 mm"
    )
    assert [item["code"] for item in payload["geometryMetrics"]] == [
        "field_of_view",
        "pixel_scale",
        "effective_focal_length",
        "effective_focal_ratio",
    ]
    assert [item["code"] for item in payload["captureMetrics"]] == [
        "sub_exposure",
        "total_integration",
        "frame_count",
        "tracking_limit",
    ]
    assert payload["notices"][0]["code"] == "target_exceeds_sensor_field"
    assert "mosaico" in payload["notices"][0]["text"]
    assert "score" not in repr(payload).casefold()


def test_c3_plan_renders_censored_integration_and_low_altitude_honestly() -> None:
    payload = _presented(
        _target(
            "caldwell-C3",
            name="C3",
            object_type="Spiral galaxy",
            magnitude="9.7",
            apparent_size="21′ × 7′",
            max_size_deg=0.35,
            altitude_deg=13.6,
            max_altitude="25°",
        ),
        altitude_deg=13.6,
        maximum_altitude_deg=25.0,
        transparency_score=40,
    )

    metrics = {
        item["code"]: (item["label"], item["value"])
        for item in payload["captureMetrics"]
    }
    notice_codes = [item["code"] for item in payload["notices"]]

    assert payload["setupText"] == (
        "Celestron NexStar 6SE + Celestron Reducer-Corrector f/6.3 "
        "+ SVBONY SV705C"
    )
    assert metrics["total_integration"] == (
        "Integrazione totale",
        "≥15 h",
    )
    assert metrics["frame_count"] == (
        "Numero minimo di pose",
        "≥6750",
    )
    assert notice_codes == [
        "target_stays_below_preferred_imaging_altitude",
        "total_integration_limit_reached",
        "field_rotation_limits_sub_exposure",
        "uncooled_camera_thermal_noise",
    ]
    assert "più notti" in payload["disclaimer"]


def test_video_presentation_uses_planetary_terms_and_condition_warnings() -> None:
    saturn = _target(
        "saturn",
        name="Saturno",
        object_type="Planet",
        magnitude="0.6",
        apparent_size="",
        max_size_deg=None,
        altitude_deg=-20,
    )

    payload = _presented(saturn, altitude_deg=-20)

    assert payload["ready"] is True
    assert payload["modeCode"] == "video"
    assert payload["modeLabel"] == "Video planetario"
    assert payload["modifierLabel"] == "Barlow 2×"
    assert payload["captureTitle"] == "Piano video"
    metrics = {
        item["code"]: item["value"]
        for item in payload["captureMetrics"]
    }
    assert metrics == {
        "clip_duration": "2–3 min",
        "planned_fps": "30–45 FPS",
        "frame_count": "3600–8100",
        "fps_source": "Massimo di catalogo",
    }
    assert payload["notices"][0]["code"] == "target_below_horizon"
    assert "massimo di catalogo" in payload["disclaimer"]


def test_camera_body_video_does_not_reuse_still_sensor_geometry() -> None:
    body = ImagingCamera(
        id="body",
        name="Sony Alpha",
        kind=ImagingCameraKind.CAMERA_BODY,
        sensor_width_mm=35.9,
        sensor_height_mm=24.0,
        resolution_width_px=6000,
        resolution_height_px=4000,
        pixel_size_um=5.98,
        bit_depth=14,
        body_type="MIRRORLESS",
        video_width_px=3840,
        video_height_px=2160,
        video_fps=30.0,
        live_view=True,
        bulb_mode=True,
    )
    recommendation = ImagingRuntimeAssembler().assemble(
        _target(
            "jupiter",
            name="Giove",
            object_type="Planet",
            magnitude="-2.1",
            apparent_size="",
            max_size_deg=None,
        ),
        ImagingRuntimeInventory(
            profile_id="1",
            telescopes=(_telescope(),),
            cameras=(body,),
        ),
        _conditions(),
    )

    payload = render_payload(
        ImagingRecommendationPresenter()
        .present(recommendation)
        .to_payload()
    )
    geometry = {
        item["code"]: (item["label"], item["value"])
        for item in payload["geometryMetrics"]
    }

    assert geometry["field_of_view"] == (
        "Campo video",
        "Non verificato",
    )
    assert geometry["pixel_scale"] == (
        "Campionamento video",
        "Non verificato",
    )
    assert payload["notices"][0]["code"] == (
        "camera_body_video_geometry_unverified"
    )
    assert "possono differire dal sensore fotografico" in (
        payload["notices"][0]["text"]
    )


def test_unavailable_presentation_guides_missing_inventory_and_solar_safety() -> None:
    assembler = ImagingRuntimeAssembler()
    missing_camera = assembler.assemble(
        _target(),
        ImagingRuntimeInventory(
            profile_id="1",
            telescopes=(_telescope(),),
        ),
    )
    missing_payload = render_payload(
        ImagingRecommendationPresenter()
        .present(missing_camera)
        .to_payload()
    )

    assert missing_payload["ready"] is False
    assert missing_payload["statusCode"] == "no_cameras"
    assert missing_payload["unavailableTitle"] == "Nessuna camera nel profilo"
    assert "camera astronomica o un corpo macchina" in missing_payload[
        "unavailableDetail"
    ]

    sun = _target(
        "sun",
        name="Sole",
        object_type="Star",
        magnitude="-26.7",
        apparent_size="0.53°",
        max_size_deg=0.53,
    )
    solar = assembler.assemble(sun, _inventory())
    assert solar.status is ImagingRuntimeStatus.TARGET_UNSUPPORTED
    solar_payload = render_payload(
        ImagingRecommendationPresenter()
        .present(solar)
        .to_payload()
    )
    assert solar_payload["stateLabel"] == "Sicurezza solare"
    assert "filtro solare certificato a tutta apertura" in solar_payload[
        "unavailableDetail"
    ]


def test_controller_property_is_on_demand_and_uses_a_dedicated_notify_signal() -> None:
    target = _target()
    recommendation = ImagingRuntimeAssembler().assemble(
        target,
        _inventory(),
        _conditions(),
    )
    controller = AppController.__new__(AppController)
    calls: list[CelestialObject] = []
    controller._photographic_detail_target = lambda: target
    controller._imaging_runtime_recommendation = lambda value: (
        calls.append(value) or recommendation
    )
    controller._imaging_recommendation_presenter = (
        ImagingRecommendationPresenter()
    )

    payload = AppController.photographicRecommendation.fget(controller)

    assert calls == [target]
    assert payload["ready"] is True
    assert payload["modeCode"] == "still"
    assert (
        '@Property("QVariant", notify=photographicRecommendationChanged)'
        in inspect.getsource(
            AppController.photographicRecommendation.fget
        )
    )

    source = inspect.getsource(AppController.__init__)
    for signal_name in (
        "selectedObjectChanged",
        "profileInventoryChanged",
        "weatherChanged",
        "skyCompassChanged",
    ):
        assert (
            f"self.{signal_name}.connect(\n"
            "            self._notify_photographic_recommendation_if_changed"
        ) in source
    assert "self.photographicRecommendationChanged.emit" not in source


def test_photographic_notify_gate_emits_only_for_a_changed_signature() -> None:
    emitted: list[bool] = []
    signature = [("target", "inventory", "conditions")]
    controller = SimpleNamespace(
        _photographic_recommendation_input_state=signature[0],
        _photographic_recommendation_input_signature=lambda: signature[0],
        photographicRecommendationChanged=SimpleNamespace(
            emit=lambda: emitted.append(True)
        ),
    )

    AppController._notify_photographic_recommendation_if_changed(controller)
    signature[0] = ("target", "changed inventory", "conditions")
    AppController._notify_photographic_recommendation_if_changed(controller)
    AppController._notify_photographic_recommendation_if_changed(controller)

    assert emitted == [True]


def test_photographic_signature_ignores_visual_only_inventory() -> None:
    target = _target()
    controller = SimpleNamespace(
        _equipment_profiles=[{"id": 1}],
        _profile_equipment={},
        _telescopes=[_telescope()],
        _reducers=[],
        _barlows=[],
        _eyepieces=["visual eyepiece"],
        _astronomy_camera_catalog=[],
        _camera_body_catalog=[],
        _sky_quality=None,
        _seeing_transparency=None,
        _moon=None,
        _moon_geometry_condition_input=lambda _target: None,
    )
    controller._active_profile_imaging_inventory = lambda: (
        ImagingRuntimeInventory(
            profile_id="1",
            telescopes=tuple(controller._telescopes),
            cameras=(_camera(),),
            reducers=tuple(controller._reducers),
            barlows=tuple(controller._barlows),
        )
    )

    initial = AppController._photographic_recommendation_input_signature(
        controller,
        target,
    )
    controller._eyepieces = ["different visual eyepiece"]
    visual_only_change = (
        AppController._photographic_recommendation_input_signature(
            controller,
            target,
        )
    )
    controller._barlows = [Barlow("barlow-3", "Barlow 3×", 3.0)]
    photographic_change = (
        AppController._photographic_recommendation_input_signature(
            controller,
            target,
        )
    )

    assert visual_only_change == initial
    assert photographic_change != initial


def test_photographic_signature_uses_only_mode_relevant_conditions() -> None:
    controller = SimpleNamespace(
        _equipment_profiles=[{"id": 1}],
        _profile_equipment={},
        _telescopes=[_telescope()],
        _reducers=[],
        _barlows=[],
        _astronomy_camera_catalog=[],
        _camera_body_catalog=[],
        _sky_quality=None,
        _moon=None,
        _moon_geometry_condition_input=lambda _target: None,
        _active_profile_imaging_inventory=lambda: _inventory(),
    )
    controller._seeing_transparency = SeeingTransparency(
        "Average",
        "Good",
        50,
        75,
        "",
        atmospheric_transparency_score=75,
    )
    deep_sky = _target()
    planet = _target(
        "jupiter",
        name="Giove",
        object_type="Planet",
        magnitude="-2.1",
        apparent_size="",
        max_size_deg=None,
    )

    still_initial = (
        AppController._photographic_recommendation_input_signature(
            controller,
            deep_sky,
        )
    )
    video_initial = (
        AppController._photographic_recommendation_input_signature(
            controller,
            planet,
        )
    )
    controller._seeing_transparency = SeeingTransparency(
        "Good",
        "Good",
        90,
        75,
        "",
        atmospheric_transparency_score=75,
    )
    still_after_seeing = (
        AppController._photographic_recommendation_input_signature(
            controller,
            deep_sky,
        )
    )
    video_after_seeing = (
        AppController._photographic_recommendation_input_signature(
            controller,
            planet,
        )
    )
    controller._seeing_transparency = SeeingTransparency(
        "Good",
        "Poor",
        90,
        40,
        "",
        atmospheric_transparency_score=40,
    )
    video_after_transparency = (
        AppController._photographic_recommendation_input_signature(
            controller,
            planet,
        )
    )
    still_after_transparency = (
        AppController._photographic_recommendation_input_signature(
            controller,
            deep_sky,
        )
    )

    assert still_after_seeing == still_initial
    assert video_after_seeing != video_initial
    assert video_after_transparency == video_after_seeing
    assert still_after_transparency != still_after_seeing


def test_object_detail_places_photographic_plan_after_visual_setup() -> None:
    source = (
        Path(__file__).parents[1]
        / "app"
        / "ui"
        / "pages"
        / "ObjectDetailPage.qml"
    ).read_text(encoding="utf-8")

    visual_index = source.index('title: qsTr("Configurazione consigliata")')
    photographic_index = source.index('title: qsTr("Piano fotografico")')
    evaluation_index = source.index('qsTr("Valutazione osservativa")')

    assert visual_index < photographic_index < evaluation_index
    assert "photographicRecommendationCard" in source
    assert "score" not in source[
        photographic_index:source.index('title: qsTr("Ciclo lunare")')
    ].casefold()
