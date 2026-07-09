from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from astro_viewer.app.models.equipment import Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.recommendation_candidate import RecommendationCandidate
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.target_observation_traits import TargetObservationTraits
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.equipment_setup_score_read_model import (
    EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER,
    EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS,
    EquipmentSetupScoreReadModel,
)
from astro_viewer.app.viewmodels.app_controller import AppController


def test_telescope_setup_score_read_model_matches_equipment_service_score() -> None:
    service = EquipmentService()
    target = _object("messier-M51", "M51", "Galaxy", "8.4", "11 arcmin", 0.18, "General")
    sky_quality = _sky_quality(3)
    seeing = _seeing(82)
    candidates = service._ranked_profile_candidates(
        target,
        [_telescope()],
        [_eyepiece("e25", "25 mm", 25.0, 52.0), _eyepiece("e10", "10 mm", 10.0, 60.0)],
        [],
        [],
        seeing,
        sky_quality,
    )

    candidate = candidates[0]
    read_model = _score_read_model(service, target, candidate, sky_quality=sky_quality, seeing=seeing)

    assert read_model.score == pytest.approx(candidate.score)
    assert read_model.unclamped_score == pytest.approx(sum(read_model.component_values().values()))
    assert read_model.component_weights() == dict(EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS)
    assert tuple(read_model.component_values()) == EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER
    assert service._configuration_score(
        TargetObservationTraits.from_object(target),
        candidate.configuration,
        service._target_profile(target, candidate.telescope, seeing, sky_quality),
        sky_quality,
        candidate.multiplier,
    ) == pytest.approx(read_model.score)


def test_binocular_setup_score_read_model_matches_equipment_service_score() -> None:
    service = EquipmentService()
    target = _object(
        "messier-M45",
        "M45",
        "Open cluster",
        "1.6",
        "110 arcmin",
        1.83,
        "WideField",
    )
    sky_quality = _sky_quality(7)
    candidates = service._ranked_profile_candidates(
        target,
        [],
        [],
        [],
        [Binocular("bino", "Nikon Monarch M5", 10, 50)],
        None,
        sky_quality,
    )

    candidate = candidates[0]
    read_model = _score_read_model(service, target, candidate, sky_quality=sky_quality, seeing=None)

    assert candidate.equipment_type == "Binocular"
    assert read_model.score == pytest.approx(candidate.score)
    assert read_model.component_values()["handling"] > 0.0
    assert "binocular stabilization" in read_model.components[-1].current_inputs


def test_setup_score_read_model_is_frozen_and_strict_json_compatible() -> None:
    service = EquipmentService()
    target = _object("saturn", "Saturno", "Pianeta", "0.8", "18 arcsec", 0.005, "HighMagnification")
    sky_quality = _sky_quality(3)
    candidates = service._ranked_profile_candidates(
        target,
        [Telescope("mak", "Mak 127", 127, 1500, "Maksutov", "GoTo")],
        [
            Eyepiece(
                "zoom",
                "Baader Hyperion Zoom 8-24 mm",
                24,
                60,
                "1.25",
                "Zoom",
                8,
                24,
                (24, 20, 16, 12, 8),
            )
        ],
        [],
        [],
        _seeing(82),
        sky_quality,
    )

    read_model = _score_read_model(
        service,
        target,
        candidates[0],
        sky_quality=sky_quality,
        seeing=_seeing(82),
    )

    json.dumps(read_model.to_dict(), sort_keys=True, allow_nan=False)
    assert read_model.runtime_policy == "preserve_equipment_service_score"
    assert read_model.nsom_policy == "setup_score_component_boundary_not_nsom_target_value"
    assert read_model.confidence_policy == "parallel_metadata_zero_score_effect"
    with pytest.raises(FrozenInstanceError):
        read_model.score = 0.0  # type: ignore[misc]


def test_setup_score_read_model_has_no_qml_or_controller_exposure() -> None:
    controller_source = inspect.getsource(AppController)
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).parents[1] / "app" / "ui").rglob("*.qml")
    )

    assert "EquipmentSetupScoreReadModel" not in controller_source
    assert "equipment_setup_score_read_model" not in controller_source
    assert "EquipmentSetupScoreReadModel" not in qml_text
    assert "equipment_setup_score_read_model" not in qml_text


def _score_read_model(
    service: EquipmentService,
    target: CelestialObject,
    candidate: RecommendationCandidate,
    *,
    sky_quality: SkyQuality,
    seeing: SeeingTransparency | None,
) -> EquipmentSetupScoreReadModel:
    traits = TargetObservationTraits.from_object(target)
    if candidate.binocular:
        profile = service._binocular_target_profile(traits, sky_quality)
    else:
        assert candidate.telescope is not None
        profile = service._target_profile(target, candidate.telescope, seeing, sky_quality)
    return service._configuration_score_read_model(
        traits,
        candidate.configuration,
        profile,
        sky_quality,
        candidate.multiplier,
    )


def _object(
    object_id: str,
    name: str,
    object_type: str,
    magnitude: str,
    apparent_size: str,
    max_angular_size_deg: float,
    recommended_observation_type: str,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="3 h",
        visible=True,
        score=80,
        difficulty="Media",
        apparent_size=apparent_size,
        max_angular_size_deg=max_angular_size_deg,
        recommended_observation_type=recommended_observation_type,
    )


def _telescope() -> Telescope:
    return Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson")


def _eyepiece(
    item_id: str,
    name: str,
    focal_length_mm: float,
    apparent_field_deg: float,
) -> Eyepiece:
    return Eyepiece(item_id, name, focal_length_mm, apparent_field_deg)


def _sky_quality(bortle: int) -> SkyQuality:
    return SkyQuality(bortle, 4.8, 20.4, "fixture", "Fixture", "test", 50.0, 20)


def _seeing(score: int) -> SeeingTransparency:
    return SeeingTransparency("Fixture", "Good", score, 70, "Fixture seeing")
