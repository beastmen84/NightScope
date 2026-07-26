from __future__ import annotations

import inspect
import math
from dataclasses import replace
from pathlib import Path

import pytest

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.imaging import (
    ImagingCamera,
    ImagingCameraKind,
)
from astro_viewer.app.models.imaging_video_capture import (
    ImagingVideoConfidence,
    ImagingVideoFpsSource,
    ImagingVideoSessionConditions,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.imaging_camera_adapter import (
    ImagingCameraAdapter,
)
from astro_viewer.app.services.imaging_recommendation_service import (
    ImagingRecommendationService,
)
from astro_viewer.app.services.imaging_train_builder import (
    ImagingTrainBuilder,
)
from astro_viewer.app.services.imaging_video_capture_advisor import (
    IMAGING_VIDEO_CAPTURE_POLICY_VERSION,
    ImagingVideoCaptureAdvisor,
)
from astro_viewer.app.viewmodels.app_controller import AppController


APP_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = APP_DIR / "data" / "schema.sql"


def _target(
    target_id: str = "jupiter",
    *,
    name: str | None = None,
    object_type: str = "Planet",
) -> CelestialObject:
    return CelestialObject(
        id=target_id,
        name=name or target_id.title(),
        object_type=object_type,
        image="",
        magnitude="-2.0",
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
    )


def _telescope(
    *,
    telescope_id: str = "scope",
    mount: str = "EQUATORIAL_TRACKING",
) -> Telescope:
    return Telescope(
        telescope_id,
        f"Scope {telescope_id}",
        200,
        2000,
        "Schmidt-Cassegrain",
        mount,
    )


def _camera(
    *,
    camera_id: str = "planetary-camera",
    kind: ImagingCameraKind = ImagingCameraKind.ASTRONOMY_CAMERA,
    full_resolution_fps: float | None = 120.0,
    video_fps: float | None = None,
    color_mode: str = "COLOR",
) -> ImagingCamera:
    return ImagingCamera(
        id=camera_id,
        name=f"Camera {camera_id}",
        kind=kind,
        sensor_width_mm=11.2,
        sensor_height_mm=6.3,
        resolution_width_px=3856,
        resolution_height_px=2180,
        pixel_size_um=2.9,
        bit_depth=12 if kind is ImagingCameraKind.ASTRONOMY_CAMERA else 14,
        camera_class=(
            "PLANETARY"
            if kind is ImagingCameraKind.ASTRONOMY_CAMERA
            else ""
        ),
        sensor_technology=(
            "CMOS"
            if kind is ImagingCameraKind.ASTRONOMY_CAMERA
            else ""
        ),
        color_mode=(
            color_mode
            if kind is ImagingCameraKind.ASTRONOMY_CAMERA
            else ""
        ),
        full_resolution_fps=full_resolution_fps,
        cooled=False,
        shutter_type="ROLLING",
        body_type=(
            "MIRRORLESS"
            if kind is ImagingCameraKind.CAMERA_BODY
            else ""
        ),
        video_width_px=(
            3840 if kind is ImagingCameraKind.CAMERA_BODY else None
        ),
        video_height_px=(
            2160 if kind is ImagingCameraKind.CAMERA_BODY else None
        ),
        video_fps=video_fps,
        live_view=kind is ImagingCameraKind.CAMERA_BODY,
        bulb_mode=kind is ImagingCameraKind.CAMERA_BODY,
    )


def _candidate(
    target_id: str = "jupiter",
    *,
    target: CelestialObject | None = None,
    telescope: Telescope | None = None,
    camera: ImagingCamera | None = None,
):
    selected_target = target or _target(target_id)
    selected_telescope = telescope or _telescope()
    configurations = ImagingTrainBuilder().build(
        [selected_telescope],
        [camera or _camera()],
    )
    solar_ids = (
        (selected_telescope.id,)
        if selected_target.id.strip().casefold() in {"sun", "sole", "sol"}
        else ()
    )
    candidate = ImagingRecommendationService().best(
        selected_target,
        configurations,
        full_aperture_solar_filter_telescope_ids=solar_ids,
    )
    assert candidate is not None
    return candidate


def _complete_conditions(
    *,
    achievable_fps: float = 90.0,
    seeing_score: int = 80,
    target_altitude_deg: float = 60.0,
) -> ImagingVideoSessionConditions:
    return ImagingVideoSessionConditions(
        achievable_fps=achievable_fps,
        seeing_score=seeing_score,
        target_altitude_deg=target_altitude_deg,
    )


def test_video_advice_is_bounded_deterministic_and_score_neutral() -> None:
    candidate = _candidate("jupiter")
    score_before = candidate.score

    advice = ImagingVideoCaptureAdvisor().advise(
        candidate,
        _complete_conditions(),
    )

    assert advice is not None
    assert advice == ImagingVideoCaptureAdvisor().advise(
        candidate,
        _complete_conditions(),
    )
    assert advice.candidate is candidate
    assert candidate.score == score_before
    assert advice.policy_version == (
        IMAGING_VIDEO_CAPTURE_POLICY_VERSION
    )
    assert advice.target_profile == "jupiter"
    assert (
        advice.clip_duration_min_seconds,
        advice.clip_duration_max_seconds,
    ) == (90, 120)
    assert advice.planned_fps_min == pytest.approx(90.0)
    assert advice.planned_fps_max == pytest.approx(90.0)
    assert advice.estimated_frame_count_min == 8100
    assert advice.estimated_frame_count_max == 10800
    assert advice.fps_source is ImagingVideoFpsSource.ACHIEVABLE
    assert advice.confidence is ImagingVideoConfidence.MEDIUM
    assert advice.data_completeness == pytest.approx(1.0)
    assert not advice.missing_inputs
    assert advice.limitation_codes == (
        "frame_exposure_gain_and_histogram_unmodeled",
        "roi_and_sensor_readout_mode_unmodeled",
        "actual_usb_and_storage_throughput_unmodeled",
        "video_codec_or_raw_format_unmodeled",
        "atmospheric_dispersion_correction_unmodeled",
        "target_apparent_diameter_and_phase_unmodeled",
        "lucky_frame_selection_fraction_unmodeled",
        "image_derotation_unmodeled",
    )


@pytest.mark.parametrize(
    (
        "target_id",
        "object_type",
        "profile",
        "duration_range",
    ),
    (
        ("sun", "Star", "solar_whole_disc", (15, 45)),
        ("moon", "Natural satellite", "lunar_whole_disc", (20, 60)),
        ("mercury", "Planet", "mercury", (120, 180)),
        ("venus", "Planet", "venus", (180, 300)),
        ("mars", "Planet", "mars", (120, 180)),
        ("jupiter", "Planet", "jupiter", (90, 120)),
        ("saturn", "Planet", "saturn", (120, 180)),
        ("uranus", "Planet", "uranus", (180, 300)),
        ("neptune", "Planet", "neptune", (180, 300)),
    ),
)
def test_solar_system_video_profiles_are_explicit(
    target_id: str,
    object_type: str,
    profile: str,
    duration_range: tuple[int, int],
) -> None:
    advice = ImagingVideoCaptureAdvisor().advise(
        _candidate(
            target=_target(
                target_id,
                object_type=object_type,
            )
        ),
        _complete_conditions(),
    )

    assert advice is not None
    assert advice.target_profile == profile
    assert (
        advice.clip_duration_min_seconds,
        advice.clip_duration_max_seconds,
    ) == duration_range


def test_localized_alias_and_unknown_planet_are_auditable() -> None:
    alias = ImagingVideoCaptureAdvisor().advise(
        _candidate(target=_target("giove")),
        _complete_conditions(),
    )
    generic = ImagingVideoCaptureAdvisor().advise(
        _candidate(target=_target("planet-x")),
        _complete_conditions(),
    )

    assert alias is not None and generic is not None
    assert alias.target_profile == "jupiter"
    assert generic.target_profile == "generic_planet"
    assert "planet_capture_profile" in generic.missing_inputs
    assert "generic_planet_capture_profile" in (
        generic.assumption_codes
    )


def test_fast_rotating_jupiter_has_a_shorter_clip_than_dim_targets() -> None:
    advisor = ImagingVideoCaptureAdvisor()
    jupiter = advisor.advise(
        _candidate("jupiter"),
        _complete_conditions(),
    )
    saturn = advisor.advise(
        _candidate("saturn"),
        _complete_conditions(),
    )
    neptune = advisor.advise(
        _candidate("neptune"),
        _complete_conditions(achievable_fps=20.0),
    )

    assert jupiter is not None and saturn is not None
    assert neptune is not None
    assert (
        jupiter.clip_duration_max_seconds
        < saturn.clip_duration_max_seconds
        < neptune.clip_duration_max_seconds
    )
    assert "planet_rotation_limits_single_clip" in (
        jupiter.warning_codes
    )
    assert "faint_planet_requires_exposure_gain_tradeoff" in (
        neptune.warning_codes
    )


def test_altaz_goto_keeps_normal_jupiter_window_and_caps_long_clips() -> None:
    advisor = ImagingVideoCaptureAdvisor()
    equatorial_jupiter = advisor.advise(
        _candidate(
            "jupiter",
            telescope=_telescope(
                telescope_id="eq",
                mount="EQUATORIAL_TRACKING",
            ),
        ),
        _complete_conditions(),
    )
    altaz_jupiter = advisor.advise(
        _candidate(
            "jupiter",
            telescope=_telescope(
                telescope_id="altaz-jupiter",
                mount="ALTAZ_GOTO",
            ),
        ),
        _complete_conditions(),
    )
    altaz_venus = advisor.advise(
        _candidate(
            "venus",
            telescope=_telescope(
                telescope_id="altaz-venus",
                mount="ALTAZ_GOTO",
            ),
        ),
        _complete_conditions(),
    )

    assert equatorial_jupiter is not None
    assert altaz_jupiter is not None
    assert altaz_venus is not None
    assert (
        altaz_jupiter.clip_duration_min_seconds,
        altaz_jupiter.clip_duration_max_seconds,
    ) == (
        equatorial_jupiter.clip_duration_min_seconds,
        equatorial_jupiter.clip_duration_max_seconds,
    )
    assert altaz_venus.clip_duration_max_seconds == 240
    assert "field_rotation_limits_long_video" in (
        altaz_jupiter.warning_codes
    )


def test_manual_mount_uses_a_short_fragmentable_clip() -> None:
    advice = ImagingVideoCaptureAdvisor().advise(
        _candidate(
            "jupiter",
            telescope=_telescope(
                mount="DOBSONIAN_MANUAL",
            ),
        ),
        _complete_conditions(),
    )

    assert advice is not None
    assert (
        advice.clip_duration_min_seconds,
        advice.clip_duration_max_seconds,
    ) == (30, 60)
    assert "manual_tracking_may_fragment_video" in (
        advice.warning_codes
    )


def test_camera_kinds_use_only_their_declared_fps_semantics() -> None:
    advisor = ImagingVideoCaptureAdvisor()
    astronomy_camera = advisor.advise(
        _candidate(
            camera=_camera(
                camera_id="astro",
                full_resolution_fps=47.0,
                video_fps=240.0,
            )
        ),
        ImagingVideoSessionConditions(
            seeing_score=80,
            target_altitude_deg=60.0,
        ),
    )
    camera_body = advisor.advise(
        _candidate(
            camera=_camera(
                camera_id="body",
                kind=ImagingCameraKind.CAMERA_BODY,
                full_resolution_fps=240.0,
                video_fps=30.0,
            )
        ),
        ImagingVideoSessionConditions(
            seeing_score=80,
            target_altitude_deg=60.0,
        ),
    )

    assert astronomy_camera is not None and camera_body is not None
    assert astronomy_camera.fps_source is (
        ImagingVideoFpsSource.CATALOG_MAXIMUM
    )
    assert astronomy_camera.planned_fps_max == pytest.approx(45.0)
    assert camera_body.planned_fps_max == pytest.approx(30.0)
    assert "camera_body_video_may_be_compressed" in (
        camera_body.warning_codes
    )
    assert "camera_body_video_geometry_not_assumed" in (
        camera_body.assumption_codes
    )
    assert {
        "video_active_sensor_area",
        "video_pixel_scale",
    }.issubset(camera_body.missing_inputs)
    assert camera_body.data_completeness < (
        astronomy_camera.data_completeness
    )


def test_achievable_fps_is_authoritative_but_not_extrapolated() -> None:
    candidate = _candidate(
        camera=_camera(full_resolution_fps=120.0)
    )
    advisor = ImagingVideoCaptureAdvisor()
    slow = advisor.advise(
        candidate,
        _complete_conditions(achievable_fps=22.5),
    )
    fast = advisor.advise(
        candidate,
        _complete_conditions(achievable_fps=240.0),
    )

    assert slow is not None and fast is not None
    assert slow.planned_fps_min == pytest.approx(22.5)
    assert slow.planned_fps_max == pytest.approx(22.5)
    assert "frame_rate_below_target_goal" in slow.warning_codes
    assert fast.planned_fps_min == pytest.approx(120.0)
    assert fast.planned_fps_max == pytest.approx(120.0)
    assert "achievable_fps_capped_to_target_goal" in (
        fast.assumption_codes
    )


def test_missing_fps_and_conditions_use_named_low_confidence_goals() -> None:
    advice = ImagingVideoCaptureAdvisor().advise(
        _candidate(
            camera=_camera(full_resolution_fps=None),
        ),
        ImagingVideoSessionConditions(),
    )

    assert advice is not None
    assert advice.fps_source is ImagingVideoFpsSource.TARGET_GOAL
    assert (
        advice.planned_fps_min,
        advice.planned_fps_max,
    ) == (30.0, 120.0)
    assert advice.confidence is ImagingVideoConfidence.LOW
    assert {
        "achievable_fps",
        "camera_fps",
        "seeing_score",
        "target_altitude",
    }.issubset(advice.missing_inputs)
    assert "target_fps_goal_without_camera_limit" in (
        advice.assumption_codes
    )


def test_invalid_conditions_fall_back_without_nonfinite_output() -> None:
    advice = ImagingVideoCaptureAdvisor().advise(
        _candidate(),
        ImagingVideoSessionConditions(
            achievable_fps=math.nan,
            seeing_score=150,
            target_altitude_deg=100.0,
        ),
    )

    assert advice is not None
    assert advice.fps_source is (
        ImagingVideoFpsSource.CATALOG_MAXIMUM
    )
    assert advice.confidence is ImagingVideoConfidence.LOW
    assert "achievable_fps_invalid" in advice.warning_codes
    assert math.isfinite(advice.planned_fps_min)
    assert math.isfinite(advice.planned_fps_max)
    assert advice.estimated_frame_count_min >= 1
    assert (
        advice.estimated_frame_count_max
        >= advice.estimated_frame_count_min
    )


def test_seeing_and_altitude_change_warnings_not_clip_duration() -> None:
    candidate = _candidate()
    advisor = ImagingVideoCaptureAdvisor()
    good = advisor.advise(
        candidate,
        _complete_conditions(
            seeing_score=85,
            target_altitude_deg=65.0,
        ),
    )
    poor = advisor.advise(
        candidate,
        _complete_conditions(
            seeing_score=25,
            target_altitude_deg=18.0,
        ),
    )

    assert good is not None and poor is not None
    assert (
        poor.clip_duration_min_seconds,
        poor.clip_duration_max_seconds,
    ) == (
        good.clip_duration_min_seconds,
        good.clip_duration_max_seconds,
    )
    assert "poor_seeing_limits_planetary_detail" in (
        poor.warning_codes
    )
    assert "low_target_altitude" in poor.warning_codes


def test_monochrome_sequence_is_not_presented_as_one_color_clip() -> None:
    advice = ImagingVideoCaptureAdvisor().advise(
        _candidate(
            camera=_camera(color_mode="MONO"),
        ),
        _complete_conditions(),
    )

    assert advice is not None
    assert (
        "monochrome_filter_sequence_must_fit_capture_window"
        in advice.warning_codes
    )


def test_sun_stays_gated_by_exact_filter_and_repeats_safety_warning() -> None:
    telescope = _telescope(telescope_id="filtered")
    configurations = ImagingTrainBuilder().build(
        [telescope],
        [_camera()],
    )
    sun = _target("sun", object_type="Star")
    service = ImagingRecommendationService()

    assert service.best(sun, configurations) is None
    candidate = service.best(
        sun,
        configurations,
        full_aperture_solar_filter_telescope_ids=("filtered",),
    )
    assert candidate is not None

    advice = ImagingVideoCaptureAdvisor().advise(
        candidate,
        _complete_conditions(),
    )

    assert advice is not None
    assert "solar_filter_integrity_must_be_verified" in (
        advice.warning_codes
    )


def test_still_candidate_has_no_video_capture_advice() -> None:
    still_candidate = _candidate(
        target=_target(
            "messier-M31",
            name="M31",
            object_type="Galaxy",
        )
    )

    assert (
        ImagingVideoCaptureAdvisor().advise(
            still_candidate,
            _complete_conditions(),
        )
        is None
    )


def test_invalid_physical_video_candidate_is_rejected() -> None:
    candidate = _candidate()
    invalid = replace(
        candidate,
        configuration=replace(
            candidate.configuration,
            pixel_scale_arcsec_per_pixel=math.inf,
        ),
    )

    assert (
        ImagingVideoCaptureAdvisor().advise(
            invalid,
            _complete_conditions(),
        )
        is None
    )


def test_all_seed_cameras_and_planets_produce_bounded_advice(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "nightscope.db"
    initialize_database(database_path, SCHEMA_PATH)
    repository = EquipmentCatalogRepository(database_path)
    cameras = ImagingCameraAdapter.from_catalogues(
        repository.astronomy_cameras(),
        repository.camera_bodies(),
    )
    configurations = ImagingTrainBuilder().build(
        [_telescope()],
        cameras,
    )
    service = ImagingRecommendationService()
    advisor = ImagingVideoCaptureAdvisor()
    conditions = ImagingVideoSessionConditions(
        seeing_score=75,
        target_altitude_deg=55.0,
    )
    target_ids = (
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
    )

    advice_count = 0
    for target_id in target_ids:
        candidates = service.rank(
            _target(target_id),
            configurations,
        )
        assert len(candidates) == 77
        for candidate in candidates:
            advice = advisor.advise(candidate, conditions)
            assert advice is not None
            assert (
                10
                <= advice.clip_duration_min_seconds
                <= advice.clip_duration_max_seconds
                <= 600
            )
            assert (
                0.5
                <= advice.planned_fps_min
                <= advice.planned_fps_max
                <= 1000.0
            )
            assert advice.estimated_frame_count_min >= 1
            assert (
                advice.estimated_frame_count_max
                >= advice.estimated_frame_count_min
            )
            advice_count += 1

    assert len(cameras) == 77
    assert advice_count == 539


def test_video_advisor_has_no_direct_controller_or_qml_registration() -> None:
    controller_source = inspect.getsource(AppController)
    equipment_source = inspect.getsource(EquipmentService)
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (APP_DIR / "app" / "ui").rglob("*.qml")
    )

    for marker in (
        "ImagingVideoCaptureAdvisor",
        "imaging_video_capture_advisor",
        "ImagingVideoSessionConditions",
    ):
        assert marker not in controller_source
        assert marker not in equipment_source
        assert marker not in qml_text
