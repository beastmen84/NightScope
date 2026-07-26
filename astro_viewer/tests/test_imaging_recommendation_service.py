from __future__ import annotations

import inspect
import math
from dataclasses import replace
from pathlib import Path

import pytest

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.catalogue_repository import CatalogueRepository
from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.models.equipment import Barlow, FocalReducer, Telescope
from astro_viewer.app.models.imaging import ImagingCamera, ImagingCameraKind
from astro_viewer.app.models.imaging_recommendation import (
    ImagingCaptureMode,
    ImagingTargetClass,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.imaging_camera_adapter import ImagingCameraAdapter
from astro_viewer.app.services.imaging_recommendation_service import (
    STILL_COMPONENT_WEIGHTS,
    VIDEO_COMPONENT_WEIGHTS,
    ImagingRecommendationService,
)
from astro_viewer.app.services.imaging_target_traits import (
    ImagingTargetTraitsAdapter,
)
from astro_viewer.app.services.imaging_train_builder import ImagingTrainBuilder
from astro_viewer.app.viewmodels.app_controller import AppController


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
    reducer_preferred: bool = True,
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
        imaging_reducer_recommended=reducer_preferred,
    )


def _telescope(
    *,
    telescope_id: str = "scope-100",
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
    camera_id: str = "camera-deep",
    kind: ImagingCameraKind = ImagingCameraKind.ASTRONOMY_CAMERA,
    camera_class: str = "DEEP_SKY",
    sensor_width_mm: float = 23.5,
    sensor_height_mm: float = 15.7,
    pixel_size_um: float = 3.76,
    bit_depth: int = 16,
    full_resolution_fps: float | None = 20.0,
    cooled: bool = True,
    backfocus_mm: float | None = 17.5,
    bulb_mode: bool = False,
    live_view: bool = False,
    video_width_px: int | None = None,
    video_height_px: int | None = None,
    video_fps: float | None = None,
) -> ImagingCamera:
    return ImagingCamera(
        id=camera_id,
        name=f"Camera {camera_id}",
        kind=kind,
        sensor_width_mm=sensor_width_mm,
        sensor_height_mm=sensor_height_mm,
        resolution_width_px=6248,
        resolution_height_px=4176,
        pixel_size_um=pixel_size_um,
        bit_depth=bit_depth,
        camera_class=camera_class,
        full_resolution_fps=full_resolution_fps,
        cooled=cooled,
        shutter_type="GLOBAL",
        backfocus_mm=backfocus_mm,
        body_type="MIRRORLESS" if kind is ImagingCameraKind.CAMERA_BODY else "",
        video_width_px=video_width_px,
        video_height_px=video_height_px,
        video_fps=video_fps,
        live_view=live_view,
        bulb_mode=bulb_mode,
    )


def _reducer(
    *,
    backfocus_mm: float = 55.0,
) -> FocalReducer:
    return FocalReducer(
        "reducer-08",
        "Reducer 0.8x",
        0.8,
        "REFRACTOR",
        backfocus_mm=backfocus_mm,
        imaging_compatible=True,
        compatible_telescope_ids=("scope-100",),
    )


def _rank(
    target: CelestialObject,
    telescopes: list[Telescope],
    cameras: list[ImagingCamera],
    *,
    reducers: list[FocalReducer] | None = None,
    barlows: list[Barlow] | None = None,
):
    configurations = ImagingTrainBuilder().build(
        telescopes,
        cameras,
        reducers or [],
        barlows or [],
    )
    return ImagingRecommendationService().rank(target, configurations)


def _catalogue_target(item: dict) -> CelestialObject:
    return _target(
        target_id=str(item["object_id"]),
        name=str(item["name"]),
        object_type=str(item["object_type"]),
        magnitude=str(item["magnitude"] or "n/d"),
        apparent_size=str(item["apparent_size"] or ""),
        max_size_deg=item["max_angular_size_deg"],
        reducer_preferred=bool(item["imaging_reducer_recommended"]),
    )


def test_target_traits_choose_still_or_video_without_visual_scores() -> None:
    galaxy = ImagingTargetTraitsAdapter.from_object(_target())
    planet = ImagingTargetTraitsAdapter.from_object(
        _target(
            target_id="jupiter",
            name="Giove",
            object_type="Pianeta",
            magnitude="-2.1",
            apparent_size="",
            max_size_deg=None,
            reducer_preferred=False,
        )
    )
    planetary_nebula = ImagingTargetTraitsAdapter.from_object(
        _target(
            target_id="messier-M57",
            name="Ring Nebula",
            object_type="Planetary nebula",
            magnitude="8.8",
            apparent_size="86″ × 62″",
            max_size_deg=86 / 3600,
            reducer_preferred=False,
        )
    )

    assert galaxy.target_class is ImagingTargetClass.GALAXY
    assert galaxy.recommended_capture_mode is ImagingCaptureMode.STILL
    assert galaxy.angular_size_major_deg == pytest.approx(3.17)
    assert galaxy.angular_size_minor_deg == pytest.approx(1.0)
    assert galaxy.reducer_preferred is True
    assert planet.target_class is ImagingTargetClass.PLANET
    assert planet.recommended_capture_mode is ImagingCaptureMode.VIDEO
    assert planetary_nebula.target_class is (
        ImagingTargetClass.PLANETARY_NEBULA
    )
    assert planetary_nebula.recommended_capture_mode is (
        ImagingCaptureMode.STILL
    )


def test_moon_gets_a_full_disk_size_and_sun_is_safely_unsupported() -> None:
    moon = ImagingTargetTraitsAdapter.from_object(
        _target(
            target_id="moon",
            name="Luna",
            object_type="Satellite",
            magnitude="-12.7",
            apparent_size="",
            max_size_deg=None,
            reducer_preferred=False,
        )
    )
    sun_target = _target(
        target_id="sun",
        name="Sole",
        object_type="Stella",
        magnitude="-26.7",
        apparent_size="",
        max_size_deg=None,
        reducer_preferred=False,
    )
    sun = ImagingTargetTraitsAdapter.from_object(sun_target)

    assert moon.target_class is ImagingTargetClass.MOON
    assert moon.angular_size_major_deg == pytest.approx(0.52)
    assert moon.angular_size_minor_deg == pytest.approx(0.52)
    assert moon.recommended_capture_mode is ImagingCaptureMode.VIDEO
    assert sun.target_class is ImagingTargetClass.SUN
    assert sun.recommendation_supported is False
    assert sun.recommended_capture_mode is None
    assert sun.unsupported_reason_code == (
        "certified_solar_filter_not_modeled"
    )
    assert _rank(sun_target, [_telescope()], [_camera()]) == []


def test_wide_galaxy_prefers_reducer_that_actually_fits_the_frame() -> None:
    candidates = _rank(
        _target(),
        [_telescope()],
        [_camera()],
        reducers=[_reducer()],
    )

    assert len(candidates) == 2
    assert candidates[0].capture_mode is ImagingCaptureMode.STILL
    assert candidates[0].configuration.reducer == _reducer()
    assert candidates[0].component_values()["framing"] > (
        candidates[1].component_values()["framing"]
    )
    assert candidates[0].score > candidates[1].score


def test_compact_galaxy_uses_finer_sampling_than_wide_galaxy() -> None:
    compact = ImagingTargetTraitsAdapter.from_object(
        _target(
            target_id="ngc-compact",
            name="Compact galaxy",
            apparent_size="3′ × 2′",
            max_size_deg=0.05,
            reducer_preferred=False,
        )
    )
    wide = ImagingTargetTraitsAdapter.from_object(_target())
    configurations = ImagingTrainBuilder().build(
        [
            _telescope(
                telescope_id="scope-fine",
                aperture_mm=100,
                focal_length_mm=900,
            ),
            _telescope(
                telescope_id="scope-wide",
                aperture_mm=100,
                focal_length_mm=450,
            ),
        ],
        [_camera(pixel_size_um=4.0)],
    )
    service = ImagingRecommendationService()

    compact_sampling = [
        service._still_sampling(compact, configuration)
        for configuration in configurations
    ]
    wide_sampling = [
        service._still_sampling(wide, configuration)
        for configuration in configurations
    ]

    assert compact.is_compact is True
    assert compact.is_extended is False
    assert compact_sampling[0] > compact_sampling[1]
    assert wide.is_extended is True
    assert wide_sampling[1] > wide_sampling[0]


def test_still_scoring_prefers_deep_sky_cooled_camera_and_bulb_body() -> None:
    deep_sky = _camera()
    planetary = _camera(
        camera_id="camera-planetary",
        camera_class="PLANETARY",
        bit_depth=12,
        full_resolution_fps=120,
        cooled=False,
    )
    bulb_body = _camera(
        camera_id="body-bulb",
        kind=ImagingCameraKind.CAMERA_BODY,
        camera_class="",
        bit_depth=14,
        full_resolution_fps=None,
        cooled=False,
        backfocus_mm=None,
        bulb_mode=True,
        live_view=True,
        video_width_px=3840,
        video_height_px=2160,
        video_fps=60,
    )
    timed_body = replace(
        bulb_body,
        id="body-timed",
        name="Camera body-timed",
        bulb_mode=False,
    )

    candidates = _rank(
        _target(reducer_preferred=False),
        [_telescope()],
        [planetary, timed_body, bulb_body, deep_sky],
    )
    scores = {
        candidate.camera.id: candidate.score
        for candidate in candidates
    }

    assert candidates[0].camera.id == "camera-deep"
    assert scores["body-bulb"] > scores["body-timed"]
    assert scores["camera-deep"] > scores["camera-planetary"]


def test_still_scoring_uses_photographic_mount_capability() -> None:
    candidates = _rank(
        _target(reducer_preferred=False),
        [
            _telescope(
                telescope_id="scope-altaz",
                mount="ALTAZ_GOTO",
            ),
            _telescope(
                telescope_id="scope-equatorial",
                mount="EQUATORIAL_TRACKING",
            ),
        ],
        [_camera()],
    )

    assert candidates[0].configuration.mount_type == (
        "EQUATORIAL_TRACKING"
    )
    assert candidates[0].component_values()["mount"] == pytest.approx(1.0)
    assert candidates[-1].component_values()["mount"] == pytest.approx(0.55)


def test_planetary_video_prefers_critical_sampling_with_barlow() -> None:
    target = _target(
        target_id="jupiter",
        name="Jupiter",
        object_type="Planet",
        magnitude="-2.1",
        apparent_size="",
        max_size_deg=None,
        reducer_preferred=False,
    )
    camera = _camera(
        camera_id="planetary-fast",
        camera_class="PLANETARY",
        sensor_width_mm=6.4,
        sensor_height_mm=4.8,
        pixel_size_um=3.75,
        bit_depth=12,
        full_resolution_fps=120,
        cooled=False,
    )
    candidates = _rank(
        target,
        [
            _telescope(
                aperture_mm=200,
                focal_length_mm=1200,
            )
        ],
        [camera],
        barlows=[Barlow("barlow-3", "Barlow 3x", 3.0)],
    )

    assert len(candidates) == 2
    assert candidates[0].capture_mode is ImagingCaptureMode.VIDEO
    assert candidates[0].configuration.barlow is not None
    assert candidates[0].configuration.barlow.multiplier == pytest.approx(3)
    assert candidates[0].component_values()["sampling"] > (
        candidates[1].component_values()["sampling"]
    )


def test_planetary_video_prefers_planetary_high_frame_rate_camera() -> None:
    target = _target(
        target_id="saturn",
        name="Saturn",
        object_type="Planet",
        magnitude="0.7",
        apparent_size="",
        max_size_deg=None,
        reducer_preferred=False,
    )
    planetary = _camera(
        camera_id="planetary-fast",
        camera_class="PLANETARY",
        pixel_size_um=3.76,
        bit_depth=12,
        full_resolution_fps=120,
        cooled=False,
    )
    deep_sky = _camera(
        camera_id="deep-slow",
        camera_class="DEEP_SKY",
        pixel_size_um=3.76,
        bit_depth=16,
        full_resolution_fps=5,
        cooled=True,
    )

    candidates = _rank(
        target,
        [_telescope(aperture_mm=200, focal_length_mm=2000)],
        [deep_sky, planetary],
    )

    assert candidates[0].camera.id == "planetary-fast"
    assert candidates[0].component_values()["camera"] > (
        candidates[-1].component_values()["camera"]
    )
    assert candidates[0].component_values()["frame_acquisition"] > (
        candidates[-1].component_values()["frame_acquisition"]
    )


def test_video_fps_semantics_remain_separate_by_camera_kind() -> None:
    target = _target(
        target_id="mars",
        name="Mars",
        object_type="Planet",
        magnitude="-1",
        apparent_size="",
        max_size_deg=None,
        reducer_preferred=False,
    )
    astronomy_camera = replace(
        _camera(
            camera_id="astronomy",
            camera_class="PLANETARY",
            full_resolution_fps=10,
            cooled=False,
        ),
        video_fps=240,
    )
    camera_body = replace(
        _camera(
            camera_id="body",
            kind=ImagingCameraKind.CAMERA_BODY,
            camera_class="",
            full_resolution_fps=240,
            cooled=False,
            backfocus_mm=None,
            live_view=True,
            video_width_px=3840,
            video_height_px=2160,
            video_fps=30,
        ),
        body_type="MIRRORLESS",
    )
    candidates = _rank(
        target,
        [_telescope(aperture_mm=200, focal_length_mm=2000)],
        [astronomy_camera, camera_body],
    )
    frame_scores = {
        candidate.camera.id: candidate.component_values()[
            "frame_acquisition"
        ]
        for candidate in candidates
    }

    assert frame_scores["astronomy"] == pytest.approx(0.35)
    assert frame_scores["body"] == pytest.approx(0.6625)


def test_full_moon_framing_can_outweigh_unusable_magnification() -> None:
    target = _target(
        target_id="moon",
        name="Moon",
        object_type="Satellite",
        magnitude="-12.7",
        apparent_size="",
        max_size_deg=None,
        reducer_preferred=False,
    )
    camera = _camera(
        camera_id="lunar",
        camera_class="PLANETARY",
        sensor_width_mm=13.2,
        sensor_height_mm=8.8,
        pixel_size_um=3.75,
        bit_depth=12,
        full_resolution_fps=60,
        cooled=False,
    )
    candidates = _rank(
        target,
        [_telescope(aperture_mm=100, focal_length_mm=500)],
        [camera],
        barlows=[Barlow("barlow-3", "Barlow 3x", 3.0)],
    )

    assert candidates[0].configuration.barlow is None
    assert candidates[0].component_values()["framing"] > 0.8
    assert candidates[-1].component_values()["framing"] < 0.1


def test_negative_reducer_spacing_is_not_ranked_as_a_usable_train() -> None:
    candidates = _rank(
        _target(),
        [_telescope()],
        [_camera(backfocus_mm=17.5)],
        reducers=[_reducer(backfocus_mm=10.0)],
    )

    assert len(candidates) == 1
    assert candidates[0].configuration.reducer is None


def test_score_is_additive_bounded_and_confidence_is_parallel() -> None:
    target = _target(
        magnitude="n/d",
        apparent_size="",
        max_size_deg=None,
        reducer_preferred=False,
    )
    candidate = _rank(target, [_telescope()], [_camera()])[0]

    assert tuple(candidate.component_values()) == tuple(
        STILL_COMPONENT_WEIGHTS
    )
    assert sum(
        component.weight for component in candidate.components
    ) == pytest.approx(100.0)
    assert candidate.score == pytest.approx(
        sum(candidate.component_points().values())
    )
    assert 0 <= candidate.score <= 100
    assert candidate.data_completeness < 1.0
    assert "target_angular_size" in candidate.missing_inputs
    assert "target_magnitude" in candidate.missing_inputs
    assert "mechanical_connection" in candidate.missing_inputs
    assert "image_circle" in candidate.missing_inputs
    assert "seeing" in candidate.missing_inputs
    assert "sky_background" in candidate.missing_inputs
    assert "tracking_accuracy" in candidate.missing_inputs
    assert all(
        component.name != "data_completeness"
        for component in candidate.components
    )


def test_data_completeness_does_not_change_the_suitability_score() -> None:
    known_backfocus = _camera(camera_id="known-backfocus")
    unknown_backfocus = replace(
        known_backfocus,
        id="unknown-backfocus",
        name="Camera unknown-backfocus",
        backfocus_mm=None,
    )
    candidates = _rank(
        _target(),
        [_telescope()],
        [known_backfocus, unknown_backfocus],
        reducers=[_reducer()],
    )
    reducer_candidates = {
        candidate.camera.id: candidate
        for candidate in candidates
        if candidate.configuration.reducer is not None
    }

    assert reducer_candidates["known-backfocus"].score == pytest.approx(
        reducer_candidates["unknown-backfocus"].score
    )
    assert (
        reducer_candidates["known-backfocus"].data_completeness
        > reducer_candidates["unknown-backfocus"].data_completeness
    )
    assert "camera_backfocus" not in (
        reducer_candidates["known-backfocus"].missing_inputs
    )
    assert "camera_backfocus" in (
        reducer_candidates["unknown-backfocus"].missing_inputs
    )


def test_visual_and_observability_scores_never_enter_imaging_ranking() -> None:
    target = _target(reducer_preferred=False)
    visual_variant = replace(
        target,
        visible=False,
        max_altitude="-10°",
        score=100,
        intrinsic_score=1,
    )
    configurations = ImagingTrainBuilder().build(
        [_telescope()],
        [_camera()],
    )
    service = ImagingRecommendationService()

    assert service.rank(target, configurations) == service.rank(
        visual_variant,
        configurations,
    )


def test_real_camera_catalogue_produces_finite_still_and_video_rankings(
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
    still_candidates = service.rank(_target(), configurations)
    video_candidates = service.rank(
        _target(
            target_id="jupiter",
            name="Jupiter",
            object_type="Planet",
            magnitude="-2.1",
            apparent_size="",
            max_size_deg=None,
            reducer_preferred=False,
        ),
        configurations,
    )
    catalogue_targets = [
        ImagingTargetTraitsAdapter.from_object(_catalogue_target(item))
        for item in CatalogueRepository(database_path).list_objects()
    ]

    assert len(cameras) == 77
    assert len(catalogue_targets) == 7585
    assert sum(
        target.has_known_angular_size
        for target in catalogue_targets
    ) == 7155
    assert all(
        target.recommendation_supported
        and target.recommended_capture_mode is ImagingCaptureMode.STILL
        and target.target_class is not ImagingTargetClass.UNKNOWN
        for target in catalogue_targets
    )
    assert len(still_candidates) == 77
    assert len(video_candidates) == 77
    assert len(
        {candidate.candidate_id for candidate in still_candidates}
    ) == 77
    assert all(
        candidate.capture_mode is ImagingCaptureMode.STILL
        and math.isfinite(candidate.score)
        and 0 <= candidate.score <= 100
        for candidate in still_candidates
    )
    assert all(
        candidate.capture_mode is ImagingCaptureMode.VIDEO
        and math.isfinite(candidate.score)
        and 0 <= candidate.score <= 100
        and tuple(candidate.component_values())
        == tuple(VIDEO_COMPONENT_WEIGHTS)
        for candidate in video_candidates
    )


def test_ranking_is_stable_deduplicated_and_not_runtime_registered() -> None:
    target = _target(reducer_preferred=False)
    configurations = ImagingTrainBuilder().build(
        [_telescope()],
        [
            _camera(camera_id="camera-z"),
            _camera(camera_id="camera-a"),
        ],
    )
    configuration = configurations[0]
    service = ImagingRecommendationService()

    assert service.rank(target, [configuration, configuration]) == (
        service.rank(target, [configuration])
    )
    assert service.best(target, [configuration]) is not None
    assert [
        candidate.camera.id
        for candidate in service.rank(target, configurations)
    ] == ["camera-a", "camera-z"]

    controller_source = inspect.getsource(AppController)
    equipment_source = inspect.getsource(EquipmentService)
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (APP_DIR / "app" / "ui").rglob("*.qml")
    )
    for marker in (
        "ImagingRecommendationService",
        "imaging_recommendation_service",
    ):
        assert marker not in controller_source
        assert marker not in equipment_source
        assert marker not in qml_text
