"""Protect conservative still-exposure ranges across sky and setup conditions."""

from __future__ import annotations

import inspect
import math
from dataclasses import replace
from pathlib import Path

import pytest

from astro_viewer.app.database.catalogue_repository import (
    CatalogueRepository,
)
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.imaging import (
    ImagingCamera,
    ImagingCameraKind,
)
from astro_viewer.app.models.imaging_exposure import (
    ImagingExposureConfidence,
    ImagingSessionConditions,
)
from astro_viewer.app.models.imaging_recommendation import (
    ImagingCaptureMode,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.imaging_exposure_advisor import (
    IMAGING_EXPOSURE_POLICY_VERSION,
    ImagingExposureAdvisor,
)
from astro_viewer.app.services.imaging_recommendation_service import (
    ImagingRecommendationService,
)
from astro_viewer.app.services.imaging_train_builder import (
    ImagingTrainBuilder,
)
from astro_viewer.app.viewmodels.app_controller import AppController
from astro_viewer.tests.database_fixture import prepare_database


APP_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = APP_DIR / "data" / "schema.sql"


def _target(
    *,
    target_id: str = "messier-M31",
    name: str = "M31 Andromeda Galaxy",
    object_type: str = "Galaxy",
    magnitude: str = "3.4",
    apparent_size: str = "3.17° × 1°",
    max_size_deg: float | None = 3.17,
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
    )


def _telescope(
    *,
    telescope_id: str = "scope",
    aperture_mm: int = 100,
    focal_length_mm: int = 500,
    mount: str = "EQUATORIAL_TRACKING",
) -> Telescope:
    return Telescope(
        telescope_id,
        f"Scope {telescope_id}",
        aperture_mm,
        focal_length_mm,
        "Refractor",
        mount,
    )


def _camera(
    *,
    camera_id: str = "camera",
    kind: ImagingCameraKind = ImagingCameraKind.ASTRONOMY_CAMERA,
    cooled: bool = True,
    bulb_mode: bool = False,
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
        bit_depth=16 if kind is ImagingCameraKind.ASTRONOMY_CAMERA else 14,
        camera_class=(
            "DEEP_SKY"
            if kind is ImagingCameraKind.ASTRONOMY_CAMERA
            else ""
        ),
        color_mode=(
            "COLOR"
            if kind is ImagingCameraKind.ASTRONOMY_CAMERA
            else ""
        ),
        full_resolution_fps=20.0,
        cooled=cooled,
        shutter_type="ROLLING",
        body_type=(
            "MIRRORLESS"
            if kind is ImagingCameraKind.CAMERA_BODY
            else ""
        ),
        live_view=kind is ImagingCameraKind.CAMERA_BODY,
        bulb_mode=bulb_mode,
    )


def _candidate(
    *,
    target: CelestialObject | None = None,
    telescope: Telescope | None = None,
    camera: ImagingCamera | None = None,
):
    configurations = ImagingTrainBuilder().build(
        [telescope or _telescope()],
        [camera or _camera()],
    )
    candidate = ImagingRecommendationService().best(
        target or _target(),
        configurations,
    )
    assert candidate is not None
    return candidate


def _complete_conditions(
    *,
    sky_brightness: float = 21.5,
    transparency: int = 80,
) -> ImagingSessionConditions:
    return ImagingSessionConditions(
        sky_brightness_mag_arcsec2=sky_brightness,
        bortle_class=3,
        transparency_score=transparency,
        target_current_altitude_deg=52.0,
        target_maximum_altitude_deg=60.0,
        moon_illumination_fraction=0.2,
        moon_altitude_deg=-5.0,
        moon_target_separation_deg=120.0,
        moon_visible_during_target_window=False,
    )


def _catalogue_target(item: dict) -> CelestialObject:
    return _target(
        target_id=str(item["object_id"]),
        name=str(item["name"]),
        object_type=str(item["object_type"]),
        magnitude=str(item["magnitude"] or "n/d"),
        apparent_size=str(item["apparent_size"] or ""),
        max_size_deg=item["max_angular_size_deg"],
    )


def test_advice_is_finite_auditable_and_score_neutral() -> None:
    candidate = _candidate()
    score_before = candidate.score

    advice = ImagingExposureAdvisor().advise(
        candidate,
        _complete_conditions(),
    )

    assert advice is not None
    assert advice == ImagingExposureAdvisor().advise(
        candidate,
        _complete_conditions(),
    )
    assert advice.candidate is candidate
    assert candidate.score == score_before
    assert advice.policy_version == IMAGING_EXPOSURE_POLICY_VERSION
    assert 0.25 <= advice.sub_exposure_min_seconds
    assert (
        advice.sub_exposure_min_seconds
        <= advice.sub_exposure_max_seconds
        <= advice.tracking_limit_seconds
    )
    assert (
        15
        <= advice.total_integration_min_minutes
        <= advice.total_integration_max_minutes
        <= 900
    )
    assert advice.estimated_frame_count_min >= 1
    assert (
        advice.estimated_frame_count_max
        >= advice.estimated_frame_count_min
    )
    assert advice.confidence is ImagingExposureConfidence.MEDIUM
    assert advice.data_completeness == pytest.approx(1.0)
    assert tuple(advice.factor_values()) == (
        "optical_speed",
        "sky_background",
        "transparency",
        "moonlight",
        "target_brightness",
    )
    assert advice.limitation_codes == (
        "camera_gain_or_iso_unmodeled",
        "camera_read_noise_unmodeled",
        "autoguiding_unmodeled",
        "tracking_accuracy_unmodeled",
        "filter_passband_unmodeled",
    )


def test_dark_sky_allows_longer_subs_but_needs_less_total_integration() -> None:
    candidate = _candidate()
    advisor = ImagingExposureAdvisor()

    dark = advisor.advise(
        candidate,
        _complete_conditions(sky_brightness=21.8),
    )
    bright = advisor.advise(
        candidate,
        _complete_conditions(sky_brightness=18.5),
    )

    assert dark is not None and bright is not None
    assert (
        dark.sub_exposure_max_seconds
        > bright.sub_exposure_max_seconds
    )
    assert (
        dark.total_integration_min_minutes
        < bright.total_integration_min_minutes
    )
    assert (
        dark.factor_values()["sky_background"][0]
        > bright.factor_values()["sky_background"][0]
    )
    assert (
        dark.factor_values()["sky_background"][1]
        < bright.factor_values()["sky_background"][1]
    )


def test_tracking_cap_does_not_make_the_lower_sub_bound_drop() -> None:
    before = ImagingExposureAdvisor._sub_exposure_range(15.25, 10.0)
    after = ImagingExposureAdvisor._sub_exposure_range(15.5, 10.0)

    assert before == (5.0, 10.0)
    assert after == (5.0, 10.0)


@pytest.mark.parametrize(
    "tracking_limit",
    (1.0, 2.0, 3.0, 5.0, 10.0, 12.0, 20.0, 30.0, 90.0),
)
def test_sub_exposure_range_is_monotonic_across_tracking_caps(
    tracking_limit: float,
) -> None:
    previous_lower = 0.0
    previous_upper = 0.0

    for quarter_seconds in range(1, 3601):
        desired = quarter_seconds / 4.0
        lower, upper = ImagingExposureAdvisor._sub_exposure_range(
            desired,
            tracking_limit,
        )

        assert previous_lower <= lower
        assert previous_upper <= upper
        assert 0.25 <= lower <= upper <= tracking_limit
        previous_lower = lower
        previous_upper = upper


def test_slow_optics_increase_integration_but_tracking_remains_a_cap() -> None:
    fast = _candidate(
        telescope=_telescope(
            telescope_id="fast",
            focal_length_mm=400,
        )
    )
    slow = _candidate(
        telescope=_telescope(
            telescope_id="slow",
            focal_length_mm=800,
        )
    )
    advisor = ImagingExposureAdvisor()

    fast_advice = advisor.advise(fast, _complete_conditions())
    slow_advice = advisor.advise(slow, _complete_conditions())

    assert fast_advice is not None and slow_advice is not None
    assert (
        slow_advice.total_integration_min_minutes
        > fast_advice.total_integration_min_minutes
    )
    assert (
        slow_advice.factor_values()["optical_speed"][1]
        > fast_advice.factor_values()["optical_speed"][1]
    )
    assert (
        slow_advice.tracking_limit_seconds
        < fast_advice.tracking_limit_seconds
    )
    assert (
        slow_advice.sub_exposure_max_seconds
        <= slow_advice.tracking_limit_seconds
    )


def test_integration_ceiling_is_reported_as_a_lower_bound() -> None:
    candidate = _candidate(
        target=_target(
            target_id="caldwell-C3",
            name="C3",
            object_type="Spiral galaxy",
            magnitude="9.7",
            apparent_size="21′ × 7′",
            max_size_deg=0.35,
        ),
        telescope=_telescope(
            aperture_mm=150,
            focal_length_mm=1500,
            mount="ALTAZ_GOTO",
        ),
    )

    advice = ImagingExposureAdvisor().advise(
        candidate,
        _complete_conditions(
            sky_brightness=20.5,
            transparency=75,
        ),
    )

    assert advice is not None
    assert advice.total_integration_min_minutes == 900
    assert advice.total_integration_max_minutes == 900
    assert advice.total_integration_min_is_lower_bound is True
    assert advice.total_integration_max_is_lower_bound is True
    assert advice.estimated_frame_count_min == 6750
    assert advice.estimated_frame_count_max == 13500
    assert "total_integration_limit_reached" in advice.warning_codes


def test_low_deep_sky_altitude_is_an_explicit_photographic_warning() -> None:
    advice = ImagingExposureAdvisor().advise(
        _candidate(),
        replace(
            _complete_conditions(),
            target_current_altitude_deg=13.6,
            target_maximum_altitude_deg=25.0,
        ),
    )

    assert advice is not None
    assert (
        "target_stays_below_preferred_imaging_altitude"
        in advice.warning_codes
    )
    assert "low_target_altitude" not in advice.warning_codes


def test_mount_taxonomy_sets_conservative_distinct_limits() -> None:
    advisor = ImagingExposureAdvisor()
    equatorial = advisor.advise(
        _candidate(
            telescope=_telescope(
                telescope_id="eq",
                mount="EQUATORIAL_TRACKING",
            )
        ),
        _complete_conditions(),
    )
    altaz = advisor.advise(
        _candidate(
            telescope=_telescope(
                telescope_id="altaz",
                mount="ALTAZ_GOTO",
            )
        ),
        _complete_conditions(),
    )
    manual = advisor.advise(
        _candidate(
            telescope=_telescope(
                telescope_id="manual",
                mount="DOBSONIAN_MANUAL",
            )
        ),
        _complete_conditions(),
    )

    assert equatorial is not None
    assert altaz is not None
    assert manual is not None
    assert (
        equatorial.tracking_limit_seconds
        > altaz.tracking_limit_seconds
        > manual.tracking_limit_seconds
    )
    assert "field_rotation_limits_sub_exposure" in (
        altaz.warning_codes
    )
    assert "manual_tracking_limits_sub_exposure" in (
        manual.warning_codes
    )


def test_bright_close_moon_shortens_subs_and_increases_integration() -> None:
    candidate = _candidate()
    advisor = ImagingExposureAdvisor()
    moon_free = advisor.advise(
        candidate,
        _complete_conditions(),
    )
    bright_moon = advisor.advise(
        candidate,
        ImagingSessionConditions(
            sky_brightness_mag_arcsec2=21.5,
            transparency_score=80,
            moon_illumination_fraction=0.95,
            moon_altitude_deg=60.0,
            moon_target_separation_deg=15.0,
            moon_visible_during_target_window=True,
        ),
    )

    assert moon_free is not None and bright_moon is not None
    assert (
        bright_moon.sub_exposure_max_seconds
        < moon_free.sub_exposure_max_seconds
    )
    assert (
        bright_moon.total_integration_min_minutes
        > moon_free.total_integration_min_minutes
    )
    assert "strong_moonlight" in bright_moon.warning_codes


def test_target_magnitude_changes_compact_target_integration() -> None:
    bright_cluster = _candidate(
        target=_target(
            target_id="bright-cluster",
            name="Bright open cluster",
            object_type="Open cluster",
            magnitude="2.0",
            apparent_size="30′",
            max_size_deg=0.5,
        )
    )
    faint_cluster = _candidate(
        target=_target(
            target_id="faint-cluster",
            name="Faint open cluster",
            object_type="Open cluster",
            magnitude="10.0",
            apparent_size="30′",
            max_size_deg=0.5,
        )
    )
    advisor = ImagingExposureAdvisor()

    bright = advisor.advise(bright_cluster, _complete_conditions())
    faint = advisor.advise(faint_cluster, _complete_conditions())

    assert bright is not None and faint is not None
    assert (
        faint.total_integration_min_minutes
        > bright.total_integration_min_minutes
    )
    assert (
        faint.factor_values()["target_brightness"][1]
        > bright.factor_values()["target_brightness"][1]
    )
    assert "target_integrated_magnitude_proxy" in (
        faint.assumption_codes
    )


def test_missing_conditions_are_explicit_and_reduce_confidence() -> None:
    advice = ImagingExposureAdvisor().advise(
        _candidate(),
        ImagingSessionConditions(),
    )

    assert advice is not None
    assert advice.confidence is ImagingExposureConfidence.LOW
    assert advice.data_completeness == pytest.approx(0.5)
    assert {
        "sky_background",
        "transparency",
        "moon_illumination",
        "moon_altitude",
        "moon_target_separation",
        "moon_window_visibility",
    }.issubset(advice.missing_inputs)
    assert "neutral_sky_background" in advice.assumption_codes
    assert "neutral_transparency" in advice.assumption_codes
    assert (
        "neutral_moonlight_without_complete_geometry"
        in advice.assumption_codes
    )


def test_bortle_is_an_explicit_sky_brightness_fallback() -> None:
    advice = ImagingExposureAdvisor().advise(
        _candidate(),
        replace(
            _complete_conditions(),
            sky_brightness_mag_arcsec2=None,
            bortle_class=4,
        ),
    )

    assert advice is not None
    assert "sky_background" not in advice.missing_inputs
    assert "sky_brightness_estimated_from_bortle" in (
        advice.assumption_codes
    )


def test_camera_body_without_bulb_is_capped_and_reported() -> None:
    candidate = _candidate(
        camera=_camera(
            camera_id="body-no-bulb",
            kind=ImagingCameraKind.CAMERA_BODY,
            cooled=False,
            bulb_mode=False,
        )
    )

    advice = ImagingExposureAdvisor().advise(
        candidate,
        _complete_conditions(),
    )

    assert advice is not None
    assert advice.tracking_limit_seconds <= 30.0
    assert advice.sub_exposure_max_seconds <= 30.0
    assert "bulb_mode_unavailable" in advice.warning_codes
    assert "camera_long_exposure_mode" in advice.missing_inputs


def test_video_candidate_has_no_still_exposure_advice() -> None:
    planet = _target(
        target_id="jupiter",
        name="Jupiter",
        object_type="Planet",
        magnitude="-2.1",
        apparent_size="",
        max_size_deg=None,
    )
    candidate = _candidate(target=planet)

    assert candidate.capture_mode is ImagingCaptureMode.VIDEO
    assert (
        ImagingExposureAdvisor().advise(
            candidate,
            _complete_conditions(),
        )
        is None
    )


def test_invalid_physical_candidate_is_rejected() -> None:
    candidate = _candidate()
    invalid = replace(
        candidate,
        configuration=replace(
            candidate.configuration,
            effective_focal_ratio=math.nan,
        ),
    )

    assert (
        ImagingExposureAdvisor().advise(
            invalid,
            _complete_conditions(),
        )
        is None
    )


def test_invalid_session_values_fall_back_without_nonfinite_output() -> None:
    advice = ImagingExposureAdvisor().advise(
        _candidate(),
        ImagingSessionConditions(
            sky_brightness_mag_arcsec2=math.nan,
            bortle_class=99,
            transparency_score=150,
            moon_illumination_fraction=2.0,
            moon_altitude_deg=100.0,
            moon_target_separation_deg=200.0,
            moon_visible_during_target_window=True,
        ),
    )

    assert advice is not None
    assert advice.confidence is ImagingExposureConfidence.LOW
    assert "neutral_sky_background" in advice.assumption_codes
    assert "neutral_transparency" in advice.assumption_codes
    assert (
        "neutral_moonlight_without_complete_geometry"
        in advice.assumption_codes
    )
    assert math.isfinite(advice.sub_exposure_min_seconds)
    assert math.isfinite(advice.sub_exposure_max_seconds)


def test_all_catalogue_targets_produce_bounded_deterministic_advice(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "nightscope.db"
    prepare_database(database_path, SCHEMA_PATH)
    configuration = ImagingTrainBuilder().build(
        [_telescope()],
        [_camera()],
    )
    recommendation_service = ImagingRecommendationService()
    advisor = ImagingExposureAdvisor()
    conditions = _complete_conditions()
    rows = CatalogueRepository(database_path).list_objects()

    for item in rows:
        candidate = recommendation_service.best(
            _catalogue_target(item),
            configuration,
        )
        assert candidate is not None
        advice = advisor.advise(candidate, conditions)
        assert advice is not None
        assert math.isfinite(advice.sub_exposure_min_seconds)
        assert math.isfinite(advice.sub_exposure_max_seconds)
        assert (
            0.25
            <= advice.sub_exposure_min_seconds
            <= advice.sub_exposure_max_seconds
            <= advice.tracking_limit_seconds
        )
        assert (
            15
            <= advice.total_integration_min_minutes
            <= advice.total_integration_max_minutes
            <= 900
        )

    assert len(rows) == 7585


def test_exposure_advisor_has_no_direct_controller_or_qml_registration() -> None:
    controller_source = inspect.getsource(AppController)
    equipment_source = inspect.getsource(EquipmentService)
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (APP_DIR / "app" / "ui").rglob("*.qml")
    )

    for marker in (
        "ImagingExposureAdvisor",
        "imaging_exposure_advisor",
        "ImagingSessionConditions",
    ):
        assert marker not in controller_source
        assert marker not in equipment_source
        assert marker not in qml_text
