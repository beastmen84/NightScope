from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro_viewer.app.models.equipment import Binocular, Eyepiece, Telescope
from astro_viewer.app.models.nsom import NsomTargetClass, nsom_to_json_compatible
from astro_viewer.app.models.observation_configuration import ObservationConfiguration
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.equipment_nsom_comparison import EquipmentNsomComparisonService
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.observer_capability_adapter import (
    build_observer_capability_from_configuration,
    build_observer_capability_projection_from_candidate,
    project_observer_capability_profile,
)


def test_configuration_adapter_builds_strict_json_observer_capability() -> None:
    capability = build_observer_capability_from_configuration(_telescope_configuration())

    json.dumps(nsom_to_json_compatible(capability), sort_keys=True, allow_nan=False)
    assert capability.light_grasp == pytest.approx((130.0 - 35.0) / (250.0 - 35.0))
    assert capability.resolution == pytest.approx((130.0 - 50.0) / (250.0 - 50.0))
    assert capability.field_of_view == pytest.approx(1.2 / 3.0)
    assert capability.magnification_range == pytest.approx(65.0 / 180.0)
    assert capability.tracking_or_goto == pytest.approx(0.2)
    assert capability.practical_comfort == pytest.approx(0.82)
    assert capability.notes[:2] == (
        "nsom:equipment_observer_capability",
        "adapter:configuration_derived",
    )


def test_binocular_configuration_projects_capability_without_sky_or_seeing_inputs() -> None:
    capability = build_observer_capability_from_configuration(_binocular_configuration())

    assert capability.light_grasp == pytest.approx((50.0 - 35.0) / (250.0 - 35.0))
    assert capability.resolution == pytest.approx(0.0)
    assert capability.field_of_view == pytest.approx(0.78)
    assert capability.magnification_range == pytest.approx(10.0 / 180.0)
    assert capability.tracking_or_goto == pytest.approx(0.15)
    assert capability.practical_comfort == pytest.approx(0.92)
    assert any(note == "binocular=Nikon 10x50" for note in capability.notes)


def test_q_target_projection_is_target_specific_but_flat_summary_is_shared() -> None:
    capability = build_observer_capability_from_configuration(_telescope_configuration())

    planet = project_observer_capability_profile(capability, NsomTargetClass.PLANET)
    galaxy = project_observer_capability_profile(capability, NsomTargetClass.GALAXY)

    assert planet.summary_for_planning == pytest.approx(galaxy.summary_for_planning)
    assert planet.q_target != pytest.approx(galaxy.q_target)
    assert planet.target_class_weighting_profile != galaxy.target_class_weighting_profile
    assert planet.derivation == "configuration_derived_adapter"
    json.dumps(nsom_to_json_compatible(planet), sort_keys=True, allow_nan=False)


def test_projection_weight_profile_is_immutable() -> None:
    capability = build_observer_capability_from_configuration(_telescope_configuration())
    projection = project_observer_capability_profile(capability, NsomTargetClass.PLANET)

    with pytest.raises(TypeError):
        projection.target_class_weighting_profile["resolution"] = 0.0

    json.dumps(nsom_to_json_compatible(projection), sort_keys=True, allow_nan=False)


def test_adapter_projection_matches_equipment_comparison_rows() -> None:
    target = _target("m51", "Galassia", observation_type="General")
    telescopes = [_medium_scope()]
    eyepieces = [_wide_eyepiece(), _planetary_eyepiece()]
    sky_quality = _sky_quality(3)
    seeing = _seeing(82)
    service = EquipmentService()
    candidate = service._ranked_profile_candidates(
        target,
        telescopes,
        eyepieces,
        [],
        [],
        seeing,
        sky_quality,
    )[0]

    comparison = EquipmentNsomComparisonService(equipment_service=service).compare(
        target,
        sky_quality=sky_quality,
        telescopes=telescopes,
        eyepieces=eyepieces,
        seeing=seeing,
        moon=_moon(),
    )
    row = next(
        item
        for item in comparison["candidates"]
        if item["candidate_id"] == candidate.configuration.configuration_id
    )
    projection = build_observer_capability_projection_from_candidate(
        candidate,
        comparison["target"]["target_class"],
    )

    assert row["nsom"]["observer_capability"]["q_target"] == pytest.approx(projection.q_target)
    assert row["nsom"]["observer_capability"]["summary_for_planning"] == pytest.approx(
        projection.summary_for_planning
    )
    assert row["nsom"]["observer_capability"]["target_class_weighting_profile"] == (
        projection.target_class_weighting_profile
    )
    assert row["nsom"]["observer_capability"]["derivation"] == projection.derivation


def test_adapter_extraction_does_not_wire_equipment_runtime_or_qml() -> None:
    root = Path(__file__).parents[1]
    controller = (root / "app" / "viewmodels" / "app_controller.py").read_text(encoding="utf-8")
    equipment_service = (root / "app" / "services" / "equipment_service.py").read_text(encoding="utf-8")
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in (root / "app" / "ui").rglob("*.qml"))

    assert "build_observer_capability_projection_from_candidate" not in controller
    assert "build_observer_capability_projection_from_candidate" not in equipment_service
    assert "ObserverCapabilityProjection" not in qml_text
    assert "observer_capability_adapter" not in qml_text


def _telescope_configuration() -> ObservationConfiguration:
    telescope = _medium_scope()
    eyepiece = _planetary_eyepiece()
    return ObservationConfiguration(
        configuration_id="telescope:130:10",
        equipment_type="Telescope",
        magnification=65.0,
        exit_pupil_mm=2.0,
        true_field_of_view_deg=1.2,
        limiting_magnitude_estimate=12.0,
        resolution_estimate=0.9,
        telescope=telescope,
        eyepiece=eyepiece,
        focal_position_mm=10.0,
        focal_position_label="10 mm",
    )


def _binocular_configuration() -> ObservationConfiguration:
    binocular = Binocular("bino-10x50", "Nikon 10x50", 10, 50)
    return ObservationConfiguration(
        configuration_id="binocular:10x50",
        equipment_type="Binocular",
        magnification=10.0,
        exit_pupil_mm=5.0,
        true_field_of_view_deg=None,
        binocular=binocular,
    )


def _target(
    object_id: str,
    object_type: str,
    *,
    observation_type: str,
    size: float = 0.2,
    magnitude: str = "6.0",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.upper(),
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="n/d",
        max_altitude="55 deg",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00-01:00",
        notes="Fixture target.",
        recommended_setup="Fixture setup",
        visibility_class="Buona",
        azimuth="180",
        time_above_horizon="4 h",
        visible=True,
        current_altitude="45 deg",
        score=86,
        difficulty="Media",
        apparent_size=f"{size} deg",
        max_angular_size_deg=size,
        recommended_observation_type=observation_type,
    )


def _medium_scope() -> Telescope:
    return Telescope("newton-130", "Newton 130/650", 130, 650, "Reflector", "manual dob")


def _wide_eyepiece() -> Eyepiece:
    return Eyepiece("wide-32", "Wide 32 mm", 32.0, 68.0)


def _planetary_eyepiece() -> Eyepiece:
    return Eyepiece("planetary-10", "Planetary 10 mm", 10.0, 60.0)


def _sky_quality(bortle: int) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=6.4,
        sky_brightness=21.4,
        source="deterministic_fixture",
        description="Observer capability adapter sky fixture.",
        confidence="high",
    )


def _seeing(score: int) -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Good" if score >= 70 else "Poor",
        transparency="Good",
        seeing_score=score,
        transparency_score=80,
        explanation="Observer capability adapter seeing fixture.",
        source="deterministic_fixture",
        confidence="high",
    )


def _moon() -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination="20%",
        rise_time="18:00",
        set_time="05:00",
        best_note="Fixture Moon.",
        image="",
        phase_angle=80.0,
    )
