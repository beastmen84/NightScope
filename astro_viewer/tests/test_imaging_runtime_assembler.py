from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

from astro_viewer.app.models.equipment import Barlow, FocalReducer, Telescope
from astro_viewer.app.models.imaging import ImagingCamera, ImagingCameraKind
from astro_viewer.app.models.imaging_exposure import ImagingSessionConditions
from astro_viewer.app.models.imaging_recommendation import ImagingCaptureMode
from astro_viewer.app.models.imaging_runtime import (
    IMAGING_RUNTIME_POLICY_VERSION,
    ImagingRuntimeConditions,
    ImagingRuntimeInventory,
    ImagingRuntimeStatus,
)
from astro_viewer.app.models.imaging_video_capture import (
    ImagingVideoSessionConditions,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.imaging_runtime_assembler import (
    ImagingRuntimeAssembler,
)
from astro_viewer.app.services.imaging_runtime_conditions_adapter import (
    ImagingRuntimeConditionsAdapter,
)
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
)
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
) -> CelestialObject:
    return CelestialObject(
        id=target_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="60°",
        direction="Sud",
        best_time="23:00",
        observing_window="21:00 - 02:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="180°",
        time_above_horizon="5 h",
        apparent_size=apparent_size,
        max_angular_size_deg=max_size_deg,
        current_altitude_degrees=altitude_deg,
    )


def _telescope(
    telescope_id: str = "scope",
    *,
    aperture_mm: int = 100,
    focal_length_mm: int = 500,
    mount: str = "EQUATORIAL_TRACKING",
) -> Telescope:
    return Telescope(
        id=telescope_id,
        name=f"Scope {telescope_id}",
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Refractor",
        mount=mount,
    )


def _camera(
    camera_id: str = "camera",
    *,
    kind: ImagingCameraKind = ImagingCameraKind.ASTRONOMY_CAMERA,
    camera_class: str = "DEEP_SKY",
    cooled: bool = True,
) -> ImagingCamera:
    return ImagingCamera(
        id=camera_id,
        name=f"Camera {camera_id}",
        kind=kind,
        sensor_width_mm=23.5,
        sensor_height_mm=15.7,
        resolution_width_px=6248,
        resolution_height_px=4176,
        pixel_size_um=3.76,
        bit_depth=16,
        camera_class=camera_class,
        color_mode="COLOR",
        full_resolution_fps=120.0,
        cooled=cooled,
        shutter_type="ROLLING",
        body_type=(
            "MIRRORLESS"
            if kind is ImagingCameraKind.CAMERA_BODY
            else ""
        ),
        video_width_px=(
            3840
            if kind is ImagingCameraKind.CAMERA_BODY
            else None
        ),
        video_height_px=(
            2160
            if kind is ImagingCameraKind.CAMERA_BODY
            else None
        ),
        video_fps=(
            60.0
            if kind is ImagingCameraKind.CAMERA_BODY
            else None
        ),
        live_view=kind is ImagingCameraKind.CAMERA_BODY,
        bulb_mode=kind is ImagingCameraKind.CAMERA_BODY,
    )


def _inventory(
    *,
    profile_id: str = "7",
    telescopes: tuple[Telescope, ...] | None = None,
    cameras: tuple[ImagingCamera, ...] | None = None,
    reducers: tuple[FocalReducer, ...] = (),
    barlows: tuple[Barlow, ...] = (),
    solar_filter_ids: tuple[str, ...] = (),
) -> ImagingRuntimeInventory:
    return ImagingRuntimeInventory(
        profile_id=profile_id,
        telescopes=telescopes if telescopes is not None else (_telescope(),),
        cameras=cameras if cameras is not None else (_camera(),),
        reducers=reducers,
        barlows=barlows,
        full_aperture_solar_filter_telescope_ids=solar_filter_ids,
    )


def _conditions() -> ImagingRuntimeConditions:
    return ImagingRuntimeConditions(
        still=ImagingSessionConditions(
            sky_brightness_mag_arcsec2=21.2,
            bortle_class=4,
            transparency_score=78,
            moon_illumination_fraction=0.42,
            moon_altitude_deg=32.0,
            moon_target_separation_deg=76.0,
            moon_visible_during_target_window=True,
        ),
        video=ImagingVideoSessionConditions(
            seeing_score=74,
            target_altitude_deg=52.0,
        ),
    )


def test_runtime_assembler_builds_and_plans_the_best_still_candidate() -> None:
    telescope = _telescope()
    reducer = FocalReducer(
        id="reducer",
        name="Reducer 0.8x",
        reduction_factor=0.8,
        optical_system="REFRACTOR",
        imaging_compatible=True,
        compatible_telescope_ids=(telescope.id,),
    )
    barlow = Barlow("barlow", "Barlow 2x", 2.0)

    result = ImagingRuntimeAssembler().assemble(
        _target(),
        _inventory(
            telescopes=(telescope,),
            reducers=(reducer,),
            barlows=(barlow,),
        ),
        _conditions(),
    )

    assert result.ready is True
    assert result.status is ImagingRuntimeStatus.READY
    assert result.policy_version == IMAGING_RUNTIME_POLICY_VERSION
    assert result.configuration_count == 3
    assert result.candidate_count == 3
    assert result.capture_mode is ImagingCaptureMode.STILL
    assert result.candidate is not None
    assert result.exposure_advice is not None
    assert result.video_advice is None
    assert result.advice is result.exposure_advice
    assert result.exposure_advice.candidate is result.candidate


def test_runtime_assembler_routes_planets_only_to_video_advice() -> None:
    result = ImagingRuntimeAssembler().assemble(
        _target(
            "jupiter",
            name="Jupiter",
            object_type="Planet",
            magnitude="-2.1",
            apparent_size="",
            max_size_deg=None,
        ),
        _inventory(
            telescopes=(
                _telescope(mount="ALTAZ_GOTO"),
            ),
            cameras=(
                _camera(
                    camera_class="PLANETARY",
                    cooled=False,
                ),
            ),
        ),
        _conditions(),
    )

    assert result.ready is True
    assert result.capture_mode is ImagingCaptureMode.VIDEO
    assert result.exposure_advice is None
    assert result.video_advice is not None
    assert result.video_advice.candidate is result.candidate
    assert result.video_advice.clip_duration_max_seconds == 120


def test_runtime_assembler_forwards_only_exact_assigned_solar_filter_ids() -> None:
    filtered = _telescope("filtered")
    unfiltered = _telescope("unfiltered")
    sun = _target(
        "sun",
        name="Sun",
        object_type="Star",
        magnitude="-26.7",
        apparent_size="",
        max_size_deg=None,
    )
    assembler = ImagingRuntimeAssembler()
    inventory = _inventory(
        telescopes=(filtered, unfiltered),
        solar_filter_ids=("missing-scope", "filtered"),
    )

    result = assembler.assemble(sun, inventory, _conditions())
    blocked = assembler.assemble(
        sun,
        replace(inventory, full_aperture_solar_filter_telescope_ids=()),
        _conditions(),
    )

    assert result.ready is True
    assert result.configuration_count == 2
    assert result.candidate_count == 1
    assert result.candidate is not None
    assert result.candidate.configuration.telescope.id == "filtered"
    assert result.video_advice is not None
    assert "solar_filter_integrity_must_be_verified" in (
        result.video_advice.warning_codes
    )
    assert blocked.status is ImagingRuntimeStatus.TARGET_UNSUPPORTED
    assert blocked.candidate is None
    assert blocked.unavailable_reason_code == (
        "certified_full_aperture_solar_filter_required"
    )


@pytest.mark.parametrize(
    ("inventory", "expected_status", "expected_reason"),
    (
        (
            _inventory(profile_id=""),
            ImagingRuntimeStatus.NO_ACTIVE_PROFILE,
            "active_profile_required",
        ),
        (
            _inventory(telescopes=()),
            ImagingRuntimeStatus.NO_TELESCOPES,
            "profile_telescope_required",
        ),
        (
            _inventory(cameras=()),
            ImagingRuntimeStatus.NO_CAMERAS,
            "profile_camera_required",
        ),
        (
            _inventory(
                telescopes=(
                    _telescope(aperture_mm=0),
                ),
            ),
            ImagingRuntimeStatus.NO_VALID_CONFIGURATIONS,
            "valid_imaging_train_required",
        ),
    ),
)
def test_runtime_assembler_returns_typed_inventory_failures(
    inventory: ImagingRuntimeInventory,
    expected_status: ImagingRuntimeStatus,
    expected_reason: str,
) -> None:
    result = ImagingRuntimeAssembler().assemble(_target(), inventory)

    assert result.ready is False
    assert result.status is expected_status
    assert result.unavailable_reason_code == expected_reason
    assert result.candidate is None
    assert result.advice is None


def test_conditions_change_advice_but_never_static_candidate_score() -> None:
    assembler = ImagingRuntimeAssembler()
    target = _target()
    inventory = _inventory()
    dark = ImagingRuntimeConditions(
        still=ImagingSessionConditions(
            sky_brightness_mag_arcsec2=21.7,
            transparency_score=85,
        )
    )
    bright = ImagingRuntimeConditions(
        still=ImagingSessionConditions(
            sky_brightness_mag_arcsec2=18.5,
            transparency_score=45,
        )
    )

    dark_result = assembler.assemble(target, inventory, dark)
    bright_result = assembler.assemble(target, inventory, bright)

    assert dark_result.candidate is not None
    assert bright_result.candidate is not None
    assert dark_result.candidate.score == bright_result.candidate.score
    assert dark_result.exposure_advice is not None
    assert bright_result.exposure_advice is not None
    assert (
        dark_result.exposure_advice.sub_exposure_max_seconds
        != bright_result.exposure_advice.sub_exposure_max_seconds
    )


def test_runtime_assembler_reports_an_unavailable_mode_advisor() -> None:
    class NoAdvice:
        @staticmethod
        def advise(
            _candidate: object,
            _conditions: object,
        ) -> None:
            return None

    assembler = ImagingRuntimeAssembler()
    assembler._exposure_advisor = NoAdvice()

    result = assembler.assemble(_target(), _inventory(), _conditions())

    assert result.status is ImagingRuntimeStatus.ADVICE_UNAVAILABLE
    assert result.candidate is not None
    assert result.advice is None
    assert result.unavailable_reason_code == "capture_advice_unavailable"


def test_runtime_conditions_adapter_uses_raw_atmospheric_transparency() -> None:
    target = _target(altitude_deg=47.5)
    conditions = ImagingRuntimeConditionsAdapter.from_runtime(
        target,
        sky_quality=SkyQuality(
            bortle_class=4,
            limiting_magnitude=6.1,
            sky_brightness=21.25,
            source="test",
            description="test",
        ),
        seeing_transparency=SeeingTransparency(
            seeing="Good",
            transparency="Average",
            seeing_score=73,
            transparency_score=49,
            atmospheric_transparency_score=82,
            explanation="test",
        ),
        moon=MoonSummary(
            phase="Waxing",
            illumination="62,5%",
            rise_time="",
            set_time="",
            best_note="",
            image="",
        ),
        moon_geometry=MoonGeometryConditionInput(
            moon_altitude_deg=31.0,
            moon_target_separation_deg=67.0,
            moon_above_horizon=True,
            moon_visible_during_target_window=True,
        ),
    )

    assert conditions.still == ImagingSessionConditions(
        sky_brightness_mag_arcsec2=21.25,
        bortle_class=4,
        transparency_score=82,
        moon_illumination_fraction=0.625,
        moon_altitude_deg=31.0,
        moon_target_separation_deg=67.0,
        moon_visible_during_target_window=True,
    )
    assert conditions.video == ImagingVideoSessionConditions(
        achievable_fps=None,
        seeing_score=73,
        target_altitude_deg=47.5,
    )


@pytest.mark.parametrize(
    ("illumination", "expected"),
    (
        ("38%", 0.38),
        ("0.38", 0.38),
        ("100", 1.0),
        ("n/d", None),
        ("125%", None),
    ),
)
def test_runtime_conditions_adapter_parses_moon_illumination_defensively(
    illumination: str,
    expected: float | None,
) -> None:
    conditions = ImagingRuntimeConditionsAdapter.from_runtime(
        _target(),
        moon=MoonSummary(
            phase="",
            illumination=illumination,
            rise_time="",
            set_time="",
            best_note="",
            image="",
        ),
    )

    assert conditions.still.moon_illumination_fraction == expected


def test_app_controller_builds_inventory_from_only_the_active_profile() -> None:
    controller = AppController.__new__(AppController)
    assigned_scope = _telescope("assigned")
    unassigned_scope = _telescope("unassigned")
    assigned_camera = _astronomy_camera_row("assigned-camera")
    unassigned_camera = _astronomy_camera_row("unassigned-camera")
    controller._equipment_profiles = [
        {"id": 7, "profile_name": "Imaging", "active": 1}
    ]
    controller._profile_equipment = {
        "7": {
            "telescope_ids": ["assigned"],
            "full_aperture_solar_filter_telescope_ids": [
                "assigned",
                "unassigned",
            ],
            "eyepiece_ids": [],
            "barlow_ids": ["barlow"],
            "binocular_ids": [],
            "filter_ids": [],
            "reducer_ids": ["reducer"],
            "astronomy_camera_ids": ["assigned-camera"],
            "camera_body_ids": ["assigned-body"],
        }
    }
    controller._telescopes = [assigned_scope, unassigned_scope]
    controller._barlows = [Barlow("barlow", "Barlow", 2.0)]
    controller._reducers = [
        FocalReducer(
            id="reducer",
            name="Reducer",
            reduction_factor=0.8,
            optical_system="REFRACTOR",
            compatible_telescope_ids=("assigned",),
        )
    ]
    controller._astronomy_camera_catalog = [
        assigned_camera,
        unassigned_camera,
    ]
    controller._camera_body_catalog = [
        _camera_body_row("assigned-body"),
        _camera_body_row("unassigned-body"),
    ]

    inventory = controller._active_profile_imaging_inventory()

    assert inventory.profile_id == "7"
    assert tuple(item.id for item in inventory.telescopes) == ("assigned",)
    assert tuple(item.id for item in inventory.cameras) == (
        "assigned-camera",
        "assigned-body",
    )
    assert tuple(item.id for item in inventory.reducers) == ("reducer",)
    assert tuple(item.id for item in inventory.barlows) == ("barlow",)
    assert inventory.full_aperture_solar_filter_telescope_ids == (
        "assigned",
    )


def test_app_controller_assembles_current_conditions_on_demand() -> None:
    controller = AppController.__new__(AppController)
    controller._equipment_profiles = [
        {"id": 7, "profile_name": "Imaging", "active": 1}
    ]
    controller._profile_equipment = {
        "7": {
            "telescope_ids": ["scope"],
            "full_aperture_solar_filter_telescope_ids": [],
            "eyepiece_ids": [],
            "barlow_ids": [],
            "binocular_ids": [],
            "filter_ids": [],
            "reducer_ids": [],
            "astronomy_camera_ids": ["camera"],
            "camera_body_ids": [],
        }
    }
    controller._telescopes = [_telescope()]
    controller._barlows = []
    controller._reducers = []
    controller._astronomy_camera_catalog = [
        _astronomy_camera_row("camera")
    ]
    controller._camera_body_catalog = []
    controller._sky_quality = SkyQuality(
        bortle_class=5,
        limiting_magnitude=5.7,
        sky_brightness=20.2,
        source="test",
        description="test",
    )
    controller._seeing_transparency = SeeingTransparency(
        seeing="Good",
        transparency="Average",
        seeing_score=71,
        transparency_score=48,
        atmospheric_transparency_score=79,
        explanation="test",
    )
    controller._moon = MoonSummary(
        phase="",
        illumination="25%",
        rise_time="",
        set_time="",
        best_note="",
        image="",
    )
    controller._moon_geometry_condition_input = lambda _target: (
        MoonGeometryConditionInput(
            moon_altitude_deg=20.0,
            moon_target_separation_deg=80.0,
            moon_visible_during_target_window=True,
        )
    )

    result = controller._imaging_runtime_recommendation(_target())

    assert result.ready is True
    assert result.profile_id == "7"
    assert result.exposure_advice is not None
    assert "sky_background" not in result.exposure_advice.missing_inputs
    assert "transparency" not in result.exposure_advice.missing_inputs
    assert "moon_illumination" not in result.exposure_advice.missing_inputs


def test_runtime_assembler_is_not_invoked_by_existing_refresh_paths() -> None:
    marker = "_imaging_runtime_recommendation"

    assert marker not in inspect.getsource(AppController._refresh_all)
    assert marker not in inspect.getsource(
        AppController._recalculate_observing_outputs
    )
    assert marker not in inspect.getsource(
        AppController._emit_profile_dependent_changes
    )


def _astronomy_camera_row(camera_id: str) -> dict[str, object]:
    return {
        "catalog_id": camera_id,
        "display_name": f"Camera {camera_id}",
        "camera_class": "DEEP_SKY",
        "sensor_technology": "CMOS",
        "color_mode": "COLOR",
        "sensor_width_mm": 23.5,
        "sensor_height_mm": 15.7,
        "resolution_width_px": 6248,
        "resolution_height_px": 4176,
        "pixel_size_um": 3.76,
        "bit_depth": 16,
        "max_fps": 3.51,
        "cooled": True,
        "cooling_delta_c": 35,
        "shutter_type": "ROLLING",
        "backfocus_mm": 17.5,
    }


def _camera_body_row(camera_id: str) -> dict[str, object]:
    return {
        "catalog_id": camera_id,
        "display_name": f"Body {camera_id}",
        "body_type": "MIRRORLESS",
        "sensor_format": "FULL_FRAME",
        "lens_mount": "Test",
        "sensor_width_mm": 36.0,
        "sensor_height_mm": 24.0,
        "resolution_width_px": 6000,
        "resolution_height_px": 4000,
        "raw_bit_depth": 14,
        "max_video_width_px": 3840,
        "max_video_height_px": 2160,
        "max_video_fps": 60,
        "live_view": True,
        "bulb_mode": True,
    }
