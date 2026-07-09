from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.equipment_nsom_comparison import EquipmentNsomComparisonService


def test_equipment_nsom_comparison_is_strict_json_and_developer_only() -> None:
    comparison = _compare(_target("m51", "Galassia", observation_type="General"))

    json.dumps(comparison, sort_keys=True, allow_nan=False)
    assert comparison["metadata"]["developer_only"] is True
    assert comparison["metadata"]["runtime_wiring"] is False
    assert comparison["metadata"]["side_effects"] == {
        "file_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "equipment_recommendations_changed": False,
        "planner_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "sky_compass_changed": False,
    }
    assert comparison["legacy_formula"]["formula"].startswith("angular_scale + magnification")
    assert comparison["candidates"]


def test_legacy_component_sum_matches_equipment_service_score() -> None:
    comparison = _compare(_target("m13", "Ammasso globulare", observation_type="General"))

    for row in comparison["candidates"]:
        legacy = row["legacy"]
        assert legacy["component_sum"] == pytest.approx(legacy["score"])
        assert sum(legacy["components"].values()) == pytest.approx(legacy["score"])
        assert legacy["score_read_model"]["score"] == pytest.approx(legacy["score"])
        assert legacy["score_read_model"]["component_values"] == legacy["components"]
        assert legacy["score_read_model"]["formula_source"] == "EquipmentService._configuration_score"
        assert "q_target:not_part_of_equipment_service_formula" in legacy["unavailable_components"]
        assert legacy["ownership_mixing"]["target_traits"]["mixed_into_equipment_score"] is True
        assert legacy["ownership_mixing"]["observer_configuration"]["mixed_into_equipment_score"] is True


def test_large_equipment_changes_q_target_and_practical_value_not_observable_value() -> None:
    target = _target("m51", "Galassia", observation_type="General")
    small = _compare(target, telescopes=[_small_scope()], eyepieces=_eyepieces())
    large = _compare(target, telescopes=[_large_scope()], eyepieces=_eyepieces())

    small_best = _top_practical_row(small)
    large_best = _top_practical_row(large)

    assert _observable_value(small_best) == pytest.approx(_observable_value(large_best))
    assert _q_target(large_best) > _q_target(small_best)
    assert _practical_value(large_best) > _practical_value(small_best)

    ownership = small_best["nsom"]["ownership"]
    assert ownership["observer_equipment_effects"]["used_in_observable_target_value"] is False
    assert ownership["observer_equipment_effects"]["used_in_practical_target_value"] is True


def test_target_class_specific_q_target_can_disagree_with_flat_summary() -> None:
    equipment = {
        "telescopes": [_small_scope(), _large_scope()],
        "eyepieces": _eyepieces(),
        "barlows": [_barlow()],
    }
    planet = _compare(_target("jupiter", "Pianeta", observation_type="HighMagnification"), **equipment)
    open_cluster = _compare(_target("m45", "Ammasso aperto", observation_type="WideField", size=1.7), **equipment)

    planet_row = _top_practical_row(planet)
    cluster_row = _top_practical_row(open_cluster)

    assert planet["target"]["target_class"] != open_cluster["target"]["target_class"]
    assert _q_target(planet_row) != pytest.approx(
        planet_row["nsom"]["observer_capability"]["summary_for_planning"]
    )
    assert _q_target(cluster_row) != pytest.approx(
        cluster_row["nsom"]["observer_capability"]["summary_for_planning"]
    )
    assert planet_row["nsom"]["observer_capability"]["target_class_weighting_profile"]
    assert cluster_row["nsom"]["observer_capability"]["target_class_weighting_profile"]


def test_sky_quality_changes_legacy_equipment_context_not_observer_capability() -> None:
    target = _target("m51", "Galassia", observation_type="General", magnitude="8.4")
    dark = _compare(target, sky_quality=_sky_quality(3), telescopes=[_medium_scope()], eyepieces=_eyepieces())
    polluted = _compare(
        target,
        sky_quality=_sky_quality(9, radiance=120.0),
        telescopes=[_medium_scope()],
        eyepieces=_eyepieces(),
    )
    candidate_id = dark["candidates"][0]["candidate_id"]
    dark_row = _row(dark, candidate_id)
    polluted_row = _row(polluted, candidate_id)

    assert polluted_row["legacy"]["components"]["light_gathering"] <= dark_row["legacy"]["components"][
        "light_gathering"
    ]
    assert _q_target(polluted_row) == pytest.approx(_q_target(dark_row))
    assert polluted_row["nsom"]["ownership"]["sky_quality_effects"]["used_in_observer_capability"] is False
    assert polluted_row["nsom"]["ownership"]["sky_quality_effects"][
        "legacy_equipment_score_uses_sky_quality"
    ] is True


def test_seeing_changes_legacy_context_not_observer_capability_for_same_configuration() -> None:
    target = _target("saturn", "Pianeta", observation_type="HighMagnification", size=0.006)
    good = _compare(target, seeing=_seeing(86), telescopes=[_mak_scope()], eyepieces=[_zoom()])
    poor = _compare(target, seeing=_seeing(30), telescopes=[_mak_scope()], eyepieces=[_zoom()])
    shared_id = next(
        row["candidate_id"]
        for row in good["candidates"]
        if any(other["candidate_id"] == row["candidate_id"] for other in poor["candidates"])
    )
    good_row = _row(good, shared_id)
    poor_row = _row(poor, shared_id)

    assert poor_row["legacy"]["components"]["seeing_compatibility"] <= good_row["legacy"]["components"][
        "seeing_compatibility"
    ]
    assert _q_target(poor_row) == pytest.approx(_q_target(good_row))
    assert poor_row["nsom"]["ownership"]["seeing_effects"]["used_in_observer_capability"] is False
    assert poor_row["nsom"]["ownership"]["seeing_effects"]["legacy_equipment_score_uses_seeing"] is True


def test_confidence_is_metadata_only_and_does_not_change_scores() -> None:
    target = _target("m51", "Galassia", observation_type="General")
    low = _compare(
        target,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = _compare(
        target,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )
    low_row = low["candidates"][0]
    high_row = _row(high, low_row["candidate_id"])

    assert low_row["nsom"]["recommendation_confidence"]["value"] < high_row["nsom"][
        "recommendation_confidence"
    ]["value"]
    assert low_row["nsom"]["recommendation_confidence"]["score_factor"] is False
    assert low_row["nsom"]["recommendation_confidence"]["score_effect"] == pytest.approx(0.0)
    assert low_row["legacy"]["score"] == pytest.approx(high_row["legacy"]["score"])
    assert _q_target(low_row) == pytest.approx(_q_target(high_row))
    assert _practical_value(low_row) == pytest.approx(_practical_value(high_row))


def test_binocular_candidate_is_projected_as_observer_capability() -> None:
    target = _target("m45", "Ammasso aperto", observation_type="WideField", size=1.7)
    comparison = _compare(target, telescopes=[], eyepieces=[], binoculars=[_binocular()])
    row = comparison["candidates"][0]

    assert row["equipment_type"] == "Binocular"
    assert row["configuration"]["binocular_id"] == "bino-10x50"
    assert row["nsom"]["observer_capability"]["field_of_view"] > 0.5
    assert row["nsom"]["observer_capability"]["practical_comfort"] > 0.8
    assert row["legacy"]["ownership_mixing"]["observer_configuration"]["mixed_into_equipment_score"] is True


def test_equipment_nsom_comparison_does_not_mutate_or_wire_runtime_outputs() -> None:
    target = _target("m51", "Galassia", observation_type="General")
    telescopes = [_small_scope(), _large_scope()]
    eyepieces = _eyepieces()
    before = (deepcopy(target), deepcopy(telescopes), deepcopy(eyepieces))

    _compare(target, telescopes=telescopes, eyepieces=eyepieces)

    assert (target, telescopes, eyepieces) == before
    app_controller = (Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).parents[1] / "app" / "ui").rglob("*.qml")
    )
    assert "EquipmentNsomComparisonService" not in app_controller
    assert "equipment_nsom_comparison" not in app_controller
    assert "EquipmentNsomComparisonService" not in qml_text
    assert "equipment_nsom_comparison" not in qml_text


def _compare(
    target: CelestialObject,
    *,
    telescopes: list[Telescope] | None = None,
    eyepieces: list[Eyepiece] | tuple[Eyepiece, ...] | None = None,
    barlows: list[Barlow] | None = None,
    binoculars: list[Binocular] | None = None,
    seeing: SeeingTransparency | None = None,
    sky_quality: SkyQuality | None = None,
    moon: MoonSummary | None = None,
    confidence: RecommendationConfidence | None = None,
) -> dict[str, object]:
    return EquipmentNsomComparisonService().compare(
        target,
        sky_quality=sky_quality or _sky_quality(3),
        telescopes=telescopes if telescopes is not None else [_medium_scope()],
        eyepieces=eyepieces if eyepieces is not None else _eyepieces(),
        barlows=barlows if barlows is not None else [],
        binoculars=binoculars if binoculars is not None else [],
        seeing=seeing or _seeing(82),
        moon=moon or _moon(20),
        confidence=confidence,
    )


def _row(comparison: dict[str, object], candidate_id: str) -> dict[str, object]:
    return next(row for row in comparison["candidates"] if row["candidate_id"] == candidate_id)


def _top_practical_row(comparison: dict[str, object]) -> dict[str, object]:
    top_id = comparison["rankings"]["nsom_practical_target_value"][0]["candidate_id"]
    return _row(comparison, top_id)


def _observable_value(row: dict[str, object]) -> float:
    return float(row["nsom"]["observable_target_value"]["value"])


def _practical_value(row: dict[str, object]) -> float:
    return float(row["nsom"]["practical_target_value"]["value"])


def _q_target(row: dict[str, object]) -> float:
    return float(row["nsom"]["observer_capability"]["q_target"])


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


def _small_scope() -> Telescope:
    return Telescope("small-70", "Small 70/500", 70, 500, "Refractor", "manual altaz")


def _medium_scope() -> Telescope:
    return Telescope("newton-130", "Newton 130/650", 130, 650, "Reflector", "manual dob")


def _large_scope() -> Telescope:
    return Telescope("large-220", "Large GoTo 220/1800", 220, 1800, "SCT", "GoTo EQ")


def _mak_scope() -> Telescope:
    return Telescope("mak-127", "Mak 127/1500", 127, 1500, "Maksutov", "tracking eq")


def _eyepieces() -> list[Eyepiece]:
    return [
        Eyepiece("wide-32", "Wide 32 mm", 32.0, 68.0),
        Eyepiece("plossl-25", "Plossl 25 mm", 25.0, 52.0),
        Eyepiece("planetary-10", "Planetary 10 mm", 10.0, 60.0),
        Eyepiece("planetary-6", "Planetary 6 mm", 6.0, 58.0),
    ]


def _zoom() -> Eyepiece:
    return Eyepiece(
        "zoom-8-24",
        "Zoom 8-24 mm",
        16.0,
        60.0,
        eyepiece_type="Zoom",
        min_focal_length_mm=8.0,
        max_focal_length_mm=24.0,
        zoom_click_positions_mm=(24.0, 20.0, 16.0, 12.0, 8.0),
    )


def _barlow() -> Barlow:
    return Barlow("barlow-2x", "2x Barlow", 2.0)


def _binocular() -> Binocular:
    return Binocular("bino-10x50", "Nikon 10x50", 10, 50)


def _sky_quality(bortle: int, *, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=6.4 if bortle <= 4 else 4.3,
        sky_brightness=21.4 if bortle <= 4 else 18.8,
        source="deterministic_fixture",
        description="Equipment NSOM comparison sky fixture.",
        confidence="high",
        viirs_radiance=radiance,
        viirs_observation_count=8 if radiance is not None else None,
    )


def _seeing(score: int) -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Good" if score >= 70 else "Poor",
        transparency="Good",
        seeing_score=score,
        transparency_score=80,
        explanation="Equipment NSOM comparison seeing fixture.",
        source="deterministic_fixture",
        confidence="high",
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="05:00",
        best_note="Fixture Moon.",
        image="",
        phase_angle=80.0,
    )
