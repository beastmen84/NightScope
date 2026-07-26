from __future__ import annotations

import pytest

from astro_viewer.app.models.equipment import Barlow, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.recommendation_candidate import RecommendationCandidate
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.equipment_service import EquipmentService


def test_fixed_eyepiece_telescope_recommendation_baseline() -> None:
    suggestion = EquipmentService().suggest_for_object(
        _object("messier-M51", "M51", "Galaxy", "8.4", "11 arcmin"),
        Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson"),
        [Eyepiece("e25", "25 mm", 25, 52), Eyepiece("e10", "10 mm", 10, 60)],
        [],
    )

    assert suggestion["setupText"] == "25 mm"
    assert suggestion["bestEyepiece"] == "25 mm"
    assert suggestion["suggestedPosition"] == "25 mm"
    assert suggestion["barlow"] == "No"
    assert suggestion["selectionScore"] == pytest.approx(87.208, abs=0.001)


def test_ranked_telescope_recommendations_use_typed_candidates() -> None:
    candidates = EquipmentService()._ranked_candidates(
        _object("messier-M51", "M51", "Galaxy", "8.4", "11 arcmin"),
        Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson"),
        [Eyepiece("e25", "25 mm", 25, 52)],
        [],
    )

    assert candidates
    assert all(isinstance(candidate, RecommendationCandidate) for candidate in candidates)
    assert candidates[0].configuration.telescope is not None
    assert candidates[0].equipment_type == "Telescope"


def test_zoom_eyepiece_recommendation_preserves_target_aware_sampling() -> None:
    suggestion = EquipmentService().suggest_for_object(
        _object("saturn", "Saturno", "Pianeta", "0.8", "18 arcsec"),
        Telescope("scope", "Newton 130/650", 130, 650, "Newton", "manuale"),
        [
            Eyepiece(
                "zoom",
                "Baader Hyperion Zoom",
                24,
                60,
                "Zoom",
                8,
                24,
            )
        ],
        [],
    )

    assert suggestion["setupText"] == "Baader Hyperion Zoom @ 8 mm"
    assert suggestion["bestEyepiece"] == "Baader Hyperion Zoom"
    assert suggestion["suggestedPosition"] == "8 mm"
    assert suggestion["barlow"] == "No"


def test_barlow_preference_for_planetary_view_is_preserved() -> None:
    suggestion = EquipmentService().suggest_for_object(
        _object("saturn", "Saturno", "Pianeta", "0.8", "18 arcsec"),
        Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale"),
        [Eyepiece("e25", "25 mm", 25, 52)],
        [Barlow("b2", "Barlow 2x", 2.0)],
    )

    assert suggestion["setupText"] == "25 mm + Barlow 2x"
    assert suggestion["bestEyepiece"] == "25 mm"
    assert suggestion["barlow"] == "Barlow 2x"


def test_wide_field_target_prefers_non_barlow_configuration() -> None:
    suggestion = EquipmentService().suggest_for_object(
        _object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin"),
        Telescope("scope", "Newton 130/650", 130, 650, "Newton", "manuale"),
        [Eyepiece("e32", "32 mm", 32, 68), Eyepiece("e8", "8 mm", 8, 60)],
        [Barlow("b2", "Barlow 2x", 2.0)],
    )

    assert suggestion["setupText"] == "32 mm"
    assert suggestion["bestEyepiece"] == "32 mm"
    assert suggestion["barlow"] == "No"


def test_poor_seeing_keeps_planetary_barlow_disabled() -> None:
    suggestion = EquipmentService().suggest_for_object(
        _object("saturn", "Saturno", "Pianeta", "0.8", "18 arcsec"),
        Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale"),
        [Eyepiece("e25", "25 mm", 25, 52)],
        [Barlow("b2", "Barlow 2x", 2.0)],
        SeeingTransparency("Poor", "Average", 30, 50, "Seeing scarso."),
    )

    assert suggestion["setupText"] == "25 mm"
    assert suggestion["barlow"] == "No"
    assert "Barlow 2x" not in suggestion["setupText"]


def test_suggest_for_profile_keeps_best_telescope_selection() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M51", "M51", "Galaxy", "8.4", "11 arcmin"),
        [
            Telescope("small", "Maksutov 90", 90, 1250, "Maksutov", "manuale"),
            Telescope("large", "Dobson 200", 200, 1200, "Newton", "Dobson"),
        ],
        [Eyepiece("e25", "25 mm", 25, 52), Eyepiece("e10", "10 mm", 10, 60)],
        [],
        None,
        SkyQuality(7, 4.6, 18.8, "test", "Urban Sky", "high", 55.0, 18),
    )

    assert suggestion["telescopeName"] == "Dobson 200"
    assert suggestion["setupText"] == "Dobson 200 + 25 mm"
    assert suggestion["bestEyepiece"] == "25 mm"
    assert suggestion["barlow"] == "No"


def _object(
    object_id: str,
    name: str,
    object_type: str,
    magnitude: str,
    apparent_size: str,
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
    )
