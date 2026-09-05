"""Protect smart-telescope capability routing across visual and imaging workflows."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.models.equipment import (
    Barlow,
    Eyepiece,
    FocalReducer,
    IntegratedImagingSystem,
    Telescope,
)
from astro_viewer.app.models.imaging import (
    ImagingCamera,
    ImagingCameraKind,
    ImagingModifierKind,
)
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
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.imaging_recommendation_presentation import (
    ImagingRecommendationPresenter,
)
from astro_viewer.app.services.imaging_runtime_assembler import (
    ImagingRuntimeAssembler,
)
from astro_viewer.app.services.imaging_train_builder import ImagingTrainBuilder
from astro_viewer.app.services.observation_configuration_builder import (
    ObservationConfigurationBuilder,
)
from astro_viewer.app.viewmodels.app_controller import AppController
from astro_viewer.tests.database_fixture import prepare_database


APP_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = APP_DIR / "data" / "schema.sql"


def _smart_telescope(
    telescope_id: str = "smart-s50",
    *,
    aperture_mm: int = 50,
    focal_length_mm: int = 250,
    sensor_model: str = "Sony IMX462",
    supports_mosaic: bool = True,
    supports_live_stacking: bool = True,
    supports_video: bool = True,
    exposure_control_mode: str = "DEVICE_MANAGED",
    supports_external_cameras: bool = False,
    supports_external_optical_modifiers: bool = False,
) -> Telescope:
    return Telescope(
        id=telescope_id,
        name=f"Smart {telescope_id}",
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Rifrattore apocromatico",
        mount="ALTAZ_GOTO",
        instrument_category="SMART_INTEGRATED",
        supports_optical_visual=False,
        supports_interchangeable_eyepieces=False,
        supports_external_cameras=supports_external_cameras,
        supports_external_optical_modifiers=(
            supports_external_optical_modifiers
        ),
        integrated_imaging=IntegratedImagingSystem(
            sensor_model=sensor_model,
            sensor_width_mm=5.568,
            sensor_height_mm=3.132,
            resolution_width_px=1920,
            resolution_height_px=1080,
            pixel_size_um=2.9,
            bit_depth=12,
            color_mode="COLOR",
            supports_live_stacking=supports_live_stacking,
            supports_video=supports_video,
            supports_mosaic=supports_mosaic,
            exposure_control_mode=exposure_control_mode,
            filter_codes=("UV_IR_CUT", "DARK", "DUAL_BAND"),
        ),
    )


def _traditional_telescope() -> Telescope:
    return Telescope(
        id="traditional-100",
        name="Traditional APO 100",
        aperture_mm=100,
        focal_length_mm=500,
        optical_type="Refractor",
        mount="EQUATORIAL_TRACKING",
    )


def _external_camera(camera_id: str = "external-camera") -> ImagingCamera:
    return ImagingCamera(
        id=camera_id,
        name=f"Camera {camera_id}",
        kind=ImagingCameraKind.ASTRONOMY_CAMERA,
        sensor_width_mm=23.5,
        sensor_height_mm=15.7,
        resolution_width_px=6248,
        resolution_height_px=4176,
        pixel_size_um=3.76,
        bit_depth=16,
        camera_class="ALL_ROUND",
        color_mode="COLOR",
        full_resolution_fps=60,
        cooled=True,
        shutter_type="ROLLING",
    )


def _target(
    target_id: str,
    *,
    name: str,
    object_type: str,
    apparent_size: str = "",
    max_size_deg: float | None = None,
) -> CelestialObject:
    return CelestialObject(
        id=target_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="8.0",
        distance="",
        max_altitude="60°",
        direction="South",
        best_time="23:00",
        observing_window="21:00 - 02:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="180°",
        time_above_horizon="5 h",
        apparent_size=apparent_size,
        max_angular_size_deg=max_size_deg,
        current_altitude_degrees=52.0,
    )


def _inventory(
    telescope: Telescope,
    *,
    cameras: tuple[ImagingCamera, ...] = (),
    reducers: tuple[FocalReducer, ...] = (),
    barlows: tuple[Barlow, ...] = (),
    solar_filter_ids: tuple[str, ...] = (),
) -> ImagingRuntimeInventory:
    return ImagingRuntimeInventory(
        profile_id="profile-smart",
        telescopes=(telescope,),
        cameras=cameras,
        reducers=reducers,
        barlows=barlows,
        full_aperture_solar_filter_telescope_ids=solar_filter_ids,
    )


def _conditions(seeing_score: int) -> ImagingRuntimeConditions:
    return ImagingRuntimeConditions(
        still=ImagingSessionConditions(
            sky_brightness_mag_arcsec2=20.9,
            bortle_class=4,
            transparency_score=75,
            target_current_altitude_deg=52,
            target_maximum_altitude_deg=60,
            moon_illumination_fraction=0.2,
            moon_altitude_deg=-5,
            moon_target_separation_deg=90,
            moon_visible_during_target_window=False,
        ),
        video=ImagingVideoSessionConditions(
            seeing_score=seeing_score,
            target_altitude_deg=52,
        ),
    )


def test_smart_domain_defaults_fail_closed_and_traditional_defaults_stay_open() -> None:
    smart = Telescope(
        id="smart-unspecified",
        name="Unspecified smart telescope",
        aperture_mm=50,
        focal_length_mm=250,
        optical_type="Refractor",
        mount="ALTAZ_GOTO",
        instrument_category="SMART_INTEGRATED",
    )
    traditional = _traditional_telescope()

    assert smart.supports_optical_visual is False
    assert smart.supports_interchangeable_eyepieces is False
    assert smart.supports_external_cameras is False
    assert smart.supports_external_optical_modifiers is False
    assert traditional.supports_optical_visual is True
    assert traditional.supports_interchangeable_eyepieces is True
    assert traditional.supports_external_cameras is True
    assert traditional.supports_external_optical_modifiers is True


def test_seeded_seestar_models_expose_verified_integrated_trains(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "nightscope.db"
    prepare_database(database_path, SCHEMA_PATH)
    repository = EquipmentCatalogRepository(database_path)

    models = {
        model["name"]: model
        for model in repository.models()
        if model["instrument_category"] == "SMART_INTEGRATED"
    }
    s30 = AppController._telescope_from_catalog_model(models["Seestar S30"])
    s50 = AppController._telescope_from_catalog_model(models["Seestar S50"])

    assert set(models) == {"Seestar S30", "Seestar S50"}
    assert (s30.aperture_mm, s30.focal_length_mm) == (30, 150)
    assert (s50.aperture_mm, s50.focal_length_mm) == (50, 250)
    assert s30.integrated_imaging is not None
    assert s50.integrated_imaging is not None
    assert s30.integrated_imaging.sensor_model == "Sony IMX662"
    assert s50.integrated_imaging.sensor_model == "Sony IMX462"
    for system in (s30.integrated_imaging, s50.integrated_imaging):
        assert system.sensor_width_mm == pytest.approx(5.568)
        assert system.sensor_height_mm == pytest.approx(3.132)
        assert system.resolution_width_px == 1920
        assert system.resolution_height_px == 1080
        assert system.pixel_size_um == pytest.approx(2.9)
        assert system.bit_depth == 12
        assert system.color_mode == "COLOR"
        assert system.supports_live_stacking
        assert system.supports_video
        assert system.supports_mosaic
        assert system.exposure_control_mode == "DEVICE_MANAGED"
        assert system.filter_codes == (
            "UV_IR_CUT",
            "DARK",
            "DUAL_BAND",
        )
        assert system.specification_source_url.startswith("https://")
    assert s30.has_complete_integrated_imaging
    assert s50.has_complete_integrated_imaging
    assert not s30.supports_interchangeable_eyepieces
    assert not s50.supports_external_cameras


def test_smart_train_ignores_unrelated_profile_equipment() -> None:
    telescope = _smart_telescope()
    reducer = FocalReducer(
        id="reducer",
        name="Reducer 0.8x",
        reduction_factor=0.8,
        optical_system="REFRACTOR",
        imaging_compatible=True,
        compatible_telescope_ids=(telescope.id,),
    )
    configurations = ImagingTrainBuilder().build(
        [telescope],
        [_external_camera()],
        reducers=[reducer],
        barlows=[Barlow("barlow", "Barlow 2x", 2.0)],
    )

    assert len(configurations) == 1
    configuration = configurations[0]
    assert configuration.camera.kind is ImagingCameraKind.SMART_INTEGRATED
    assert configuration.modifier_kind is ImagingModifierKind.NONE
    assert configuration.reducer is None
    assert configuration.barlow is None


def test_explicit_hybrid_capabilities_allow_external_photo_paths() -> None:
    telescope = _smart_telescope(
        supports_external_cameras=True,
        supports_external_optical_modifiers=True,
    )
    reducer = FocalReducer(
        id="reducer",
        name="Reducer 0.8x",
        reduction_factor=0.8,
        optical_system="REFRACTOR",
        compatible_telescope_ids=(telescope.id,),
    )
    configurations = ImagingTrainBuilder().build(
        [telescope],
        [_external_camera()],
        reducers=[reducer],
        barlows=[Barlow("barlow", "Barlow 2x", 2.0)],
    )

    assert len(configurations) == 6
    assert {
        configuration.camera.kind for configuration in configurations
    } == {
        ImagingCameraKind.SMART_INTEGRATED,
        ImagingCameraKind.ASTRONOMY_CAMERA,
    }
    assert {
        configuration.modifier_kind for configuration in configurations
    } == {
        ImagingModifierKind.NONE,
        ImagingModifierKind.FOCAL_REDUCER,
        ImagingModifierKind.BARLOW,
    }


def test_visual_engine_never_builds_fake_smart_eyepiece_configurations() -> None:
    smart = _smart_telescope()
    traditional = _traditional_telescope()
    eyepiece = Eyepiece("ep-20", "20 mm", 20, 68)
    barlow = Barlow("barlow", "Barlow 2x", 2.0)
    builder = ObservationConfigurationBuilder()

    smart_only = builder.build([smart], [eyepiece], [barlow])
    mixed = builder.build([smart, traditional], [eyepiece], [barlow])
    suggestion = EquipmentService().suggest_for_profile(
        _target(
            "messier-M42",
            name="M42",
            object_type="Diffuse nebula",
            apparent_size="1.1° × 1°",
            max_size_deg=1.1,
        ),
        [smart],
        [eyepiece],
        [barlow],
    )

    assert smart_only == []
    assert mixed
    assert all(
        configuration.telescope == traditional
        for configuration in mixed
        if configuration.telescope is not None
    )
    assert suggestion["recommendationState"] == "smart_eaa_only"
    assert suggestion["setupType"] == "naked_eye"
    assert suggestion["setupOptions"] == []
    assert suggestion["bestEyepiece"] == ""
    assert suggestion["barlow"] == "Non applicabile"
    assert "x" not in suggestion["setupText"].casefold()


def test_mixed_profile_keeps_visual_and_integrated_photo_paths_separate() -> None:
    smart = _smart_telescope()
    traditional = _traditional_telescope()
    camera = _external_camera()
    reducer = FocalReducer(
        id="reducer",
        name="Reducer 0.8x",
        reduction_factor=0.8,
        optical_system="REFRACTOR",
        compatible_telescope_ids=(traditional.id, smart.id),
    )
    configurations = ImagingTrainBuilder().build(
        [smart, traditional],
        [camera],
        reducers=[reducer],
        barlows=[Barlow("barlow", "Barlow 2x", 2.0)],
    )

    assert len(configurations) == 4
    smart_configurations = [
        configuration
        for configuration in configurations
        if configuration.telescope.id == smart.id
    ]
    traditional_configurations = [
        configuration
        for configuration in configurations
        if configuration.telescope.id == traditional.id
    ]
    assert len(smart_configurations) == 1
    assert smart_configurations[0].camera.kind is (
        ImagingCameraKind.SMART_INTEGRATED
    )
    assert smart_configurations[0].modifier_kind is ImagingModifierKind.NONE
    assert len(traditional_configurations) == 3
    assert all(
        configuration.camera.id == camera.id
        for configuration in traditional_configurations
    )


def test_incomplete_smart_specs_fail_closed_without_external_camera_fallback() -> None:
    incomplete = replace(
        _smart_telescope(),
        integrated_imaging=IntegratedImagingSystem(
            sensor_model="Unknown",
            color_mode="COLOR",
        ),
    )
    result = ImagingRuntimeAssembler().assemble(
        _target(
            "messier-M31",
            name="M31",
            object_type="Galaxy",
            apparent_size="3.17° × 1°",
            max_size_deg=3.17,
        ),
        _inventory(incomplete, cameras=(_external_camera(),)),
    )
    presentation = ImagingRecommendationPresenter().present(result)

    assert result.status is ImagingRuntimeStatus.NO_VALID_CONFIGURATIONS
    assert result.unavailable_reason_code == "smart_integrated_specs_required"
    assert presentation.ready is False
    assert result.candidate is None

    no_external_result = ImagingRuntimeAssembler().assemble(
        _target(
            "messier-M31",
            name="M31",
            object_type="Galaxy",
            apparent_size="3.17° × 1°",
            max_size_deg=3.17,
        ),
        _inventory(incomplete),
    )
    no_external_presentation = ImagingRecommendationPresenter().present(
        no_external_result
    )
    assert no_external_result.unavailable_reason_code == (
        "smart_integrated_specs_required"
    )
    assert no_external_presentation.unavailable_title == (
        "Specifiche integrate incomplete"
    )

    explicit_hybrid = replace(
        incomplete,
        supports_external_cameras=True,
    )
    hybrid_without_camera = ImagingRuntimeAssembler().assemble(
        _target(
            "messier-M31",
            name="M31",
            object_type="Galaxy",
            apparent_size="3.17° × 1°",
            max_size_deg=3.17,
        ),
        _inventory(explicit_hybrid),
    )
    hybrid_with_camera = ImagingRuntimeAssembler().assemble(
        _target(
            "messier-M31",
            name="M31",
            object_type="Galaxy",
            apparent_size="3.17° × 1°",
            max_size_deg=3.17,
        ),
        _inventory(
            explicit_hybrid,
            cameras=(_external_camera(),),
        ),
    )
    mixed_without_camera = ImagingRuntimeAssembler().assemble(
        _target(
            "messier-M31",
            name="M31",
            object_type="Galaxy",
            apparent_size="3.17° × 1°",
            max_size_deg=3.17,
        ),
        ImagingRuntimeInventory(
            profile_id="profile-mixed",
            telescopes=(incomplete, _traditional_telescope()),
        ),
    )
    assert hybrid_without_camera.status is ImagingRuntimeStatus.NO_CAMERAS
    assert hybrid_without_camera.unavailable_reason_code == (
        "profile_camera_required"
    )
    assert hybrid_with_camera.ready
    assert hybrid_with_camera.candidate is not None
    assert hybrid_with_camera.candidate.camera.kind is (
        ImagingCameraKind.ASTRONOMY_CAMERA
    )
    assert mixed_without_camera.status is ImagingRuntimeStatus.NO_CAMERAS
    assert mixed_without_camera.unavailable_reason_code == (
        "profile_camera_required"
    )


def test_smart_presentation_uses_managed_eaa_mosaic_and_sampling_guidance() -> None:
    telescope = _smart_telescope()
    assembler = ImagingRuntimeAssembler()
    presenter = ImagingRecommendationPresenter()
    m31 = _target(
        "messier-M31",
        name="M31",
        object_type="Galaxy",
        apparent_size="3.17° × 1°",
        max_size_deg=3.17,
    )
    jupiter = _target(
        "jupiter",
        name="Jupiter",
        object_type="Planet",
    )

    still = assembler.assemble(
        m31,
        _inventory(telescope),
        _conditions(75),
    )
    poor = assembler.assemble(
        jupiter,
        _inventory(telescope),
        _conditions(25),
    )
    excellent = assembler.assemble(
        jupiter,
        _inventory(telescope),
        _conditions(90),
    )
    still_payload = presenter.present(still).to_payload()
    poor_payload = presenter.present(poor).to_payload()

    assert still.ready
    assert still.configuration_count == 1
    assert still_payload["modeCode"] == "still"
    assert still_payload["modeLabel"] == "EAA / live stacking"
    assert [metric["code"] for metric in still_payload["captureMetrics"]] == [
        "sub_exposure_control",
        "total_integration",
    ]
    assert still_payload["captureMetrics"][0]["value"] == (
        "Gestite dal dispositivo"
    )
    assert "target_requires_integrated_mosaic" in {
        notice["code"] for notice in still_payload["notices"]
    }
    assert poor.candidate is not None
    assert excellent.candidate is not None
    assert poor.candidate.configuration.configuration_id == (
        excellent.candidate.configuration.configuration_id
    )
    assert poor.candidate.configuration.modifier_kind is (
        ImagingModifierKind.NONE
    )
    assert "native_scale_under_samples_planet" in {
        notice["code"] for notice in poor_payload["notices"]
    }
    assert "poor_seeing_limits_planetary_detail" in {
        notice["code"] for notice in poor_payload["notices"]
    }


def test_smart_capture_capabilities_and_exposure_control_are_not_assumed() -> None:
    assembler = ImagingRuntimeAssembler()
    presenter = ImagingRecommendationPresenter()
    galaxy = _target(
        "messier-M31",
        name="M31",
        object_type="Galaxy",
        apparent_size="3.17° × 1°",
        max_size_deg=3.17,
    )
    moon = _target("moon", name="Moon", object_type="Moon")
    video_only = _smart_telescope(supports_live_stacking=False)
    still_only = _smart_telescope(supports_video=False)
    configurable = _smart_telescope(
        exposure_control_mode="USER_CONFIGURABLE"
    )

    unavailable_still = assembler.assemble(
        galaxy,
        _inventory(video_only),
        _conditions(70),
    )
    unavailable_video = assembler.assemble(
        moon,
        _inventory(still_only),
        _conditions(70),
    )
    configurable_still = presenter.present(
        assembler.assemble(
            galaxy,
            _inventory(configurable),
            _conditions(70),
        )
    ).to_payload()

    assert unavailable_still.unavailable_reason_code == (
        "smart_capture_mode_unsupported"
    )
    assert unavailable_video.unavailable_reason_code == (
        "smart_capture_mode_unsupported"
    )
    assert presenter.present(unavailable_still).unavailable_title == (
        "Modalità di acquisizione non supportata"
    )
    assert [
        metric["code"] for metric in configurable_still["captureMetrics"]
    ] == [
        "sub_exposure",
        "total_integration",
        "frame_count",
        "tracking_limit",
    ]
    assert "Lascia al dispositivo" not in configurable_still["guidance"]


def test_smart_solar_route_still_requires_profile_safety_declaration() -> None:
    telescope = _smart_telescope()
    sun = _target("sun", name="Sun", object_type="Star")
    assembler = ImagingRuntimeAssembler()

    blocked = assembler.assemble(sun, _inventory(telescope), _conditions(70))
    allowed = assembler.assemble(
        sun,
        _inventory(telescope, solar_filter_ids=(telescope.id,)),
        _conditions(70),
    )

    assert blocked.status is ImagingRuntimeStatus.TARGET_UNSUPPORTED
    assert blocked.unavailable_reason_code == (
        "certified_full_aperture_solar_filter_required"
    )
    assert allowed.ready
    assert allowed.candidate is not None
    assert allowed.candidate.camera.kind is ImagingCameraKind.SMART_INTEGRATED


def test_smart_routing_matrix_covers_hundreds_of_profile_combinations() -> None:
    telescopes = (
        _smart_telescope(
            "smart-s30",
            aperture_mm=30,
            focal_length_mm=150,
            sensor_model="Sony IMX662",
        ),
        _smart_telescope(),
    )
    targets = (
        _target(
            "messier-M31",
            name="M31",
            object_type="Galaxy",
            apparent_size="3.17° × 1°",
            max_size_deg=3.17,
        ),
        _target(
            "messier-M42",
            name="M42",
            object_type="Diffuse nebula",
            apparent_size="1.1° × 1°",
            max_size_deg=1.1,
        ),
        _target(
            "messier-M13",
            name="M13",
            object_type="Globular cluster",
            apparent_size="0.33°",
            max_size_deg=0.33,
        ),
        _target("comet-test", name="Comet", object_type="Comet"),
        _target("moon", name="Moon", object_type="Moon"),
        _target("mars", name="Mars", object_type="Planet"),
        _target("jupiter", name="Jupiter", object_type="Planet"),
        _target("saturn", name="Saturn", object_type="Planet"),
        _target("uranus", name="Uranus", object_type="Planet"),
        _target("neptune", name="Neptune", object_type="Planet"),
        _target("sun", name="Sun", object_type="Star"),
    )
    cameras = tuple(
        _external_camera(f"external-{index}") for index in range(4)
    )
    assembler = ImagingRuntimeAssembler()
    checked = 0

    for telescope in telescopes:
        reducers = (
            (),
            (
                FocalReducer(
                    id=f"reducer-{telescope.id}",
                    name="Reducer 0.8x",
                    reduction_factor=0.8,
                    optical_system="REFRACTOR",
                    compatible_telescope_ids=(telescope.id,),
                ),
            ),
        )
        barlows = (
            (),
            (Barlow("barlow-2", "Barlow 2x", 2.0),),
        )
        for target in targets:
            for camera in cameras:
                for reducer_set in reducers:
                    for barlow_set in barlows:
                        results = [
                            assembler.assemble(
                                target,
                                _inventory(
                                    telescope,
                                    cameras=(camera,),
                                    reducers=reducer_set,
                                    barlows=barlow_set,
                                    solar_filter_ids=(
                                        (telescope.id,)
                                        if target.id == "sun"
                                        else ()
                                    ),
                                ),
                                _conditions(seeing),
                            )
                            for seeing in (25, 90)
                        ]
                        checked += len(results)
                        assert all(result.ready for result in results)
                        assert all(
                            result.configuration_count == 1
                            for result in results
                        )
                        assert all(
                            result.candidate is not None
                            and result.candidate.camera.kind
                            is ImagingCameraKind.SMART_INTEGRATED
                            and result.candidate.configuration.modifier_kind
                            is ImagingModifierKind.NONE
                            for result in results
                        )
                        assert (
                            results[0].candidate.configuration.configuration_id
                            == results[1].candidate.configuration.configuration_id
                        )

    assert checked == 704


def test_smart_visual_matrix_has_no_eyepiece_or_seeing_combinations() -> None:
    telescopes = (
        _smart_telescope(
            "smart-s30",
            aperture_mm=30,
            focal_length_mm=150,
            sensor_model="Sony IMX662",
        ),
        _smart_telescope(),
    )
    targets = tuple(
        _target(
            f"matrix-{index}",
            name=f"Matrix target {index}",
            object_type=(
                "Planet"
                if index < 8
                else "Diffuse nebula"
                if index < 17
                else "Galaxy"
            ),
            apparent_size=(
                ""
                if index < 8
                else f"{0.2 + index * 0.1:.1f}°"
            ),
            max_size_deg=(
                None if index < 8 else 0.2 + index * 0.1
            ),
        )
        for index in range(25)
    )
    eyepiece_sets = (
        (),
        (Eyepiece("wide-25", "Wide 25 mm", 25, 68),),
        (Eyepiece("planet-5", "Planet 5 mm", 5, 60),),
        (
            Eyepiece(
                "zoom",
                "Zoom 8-24 mm",
                24,
                68,
                eyepiece_type="Zoom",
                min_focal_length_mm=8,
                max_focal_length_mm=24,
                zoom_click_positions_mm=(24, 20, 16, 12, 8),
            ),
        ),
    )
    conditions = (
        None,
        SeeingTransparency("Poor", "Poor", 25, 35, "test"),
        SeeingTransparency("Average", "Average", 55, 55, "test"),
        SeeingTransparency("Excellent", "Excellent", 90, 90, "test"),
    )
    sky = SkyQuality(4, 6.1, 20.9, "test", "test")
    service = EquipmentService()
    checked = 0

    for telescope in telescopes:
        for target in targets:
            for eyepieces in eyepiece_sets:
                for seeing in conditions:
                    suggestion = service.suggest_for_profile(
                        target,
                        [telescope],
                        list(eyepieces),
                        [Barlow("barlow", "Barlow 2x", 2.0)],
                        seeing,
                        sky,
                    )
                    checked += 1
                    assert suggestion["recommendationState"] == (
                        "smart_eaa_only"
                    )
                    assert suggestion["setupOptions"] == []
                    assert suggestion["bestEyepiece"] == ""
                    assert suggestion["suggestedPosition"] == ""
                    assert suggestion["barlow"] == "Non applicabile"
                    assert suggestion["selectionScore"] in {0.0, 20.0}

    assert checked == 800
