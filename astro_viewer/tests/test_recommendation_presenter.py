"""Protect stable visual-equipment recommendation payloads and explanations."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.recommendation_presenter import RecommendationPresenter


def test_presenter_serializes_telescope_recommendation_options() -> None:
    service = EquipmentService()
    target = _object("messier-M51", "M51", "Galaxy", "8.4", "11 arcmin", 0.183, "General")
    candidates = service._ranked_candidates(
        target,
        Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson"),
        [Eyepiece("e25", "25 mm", 25, 52), Eyepiece("e10", "10 mm", 10, 60)],
        [],
    )

    dto = RecommendationPresenter().from_candidates(target, candidates, service._recommended_candidate(candidates))

    assert dto["equipmentType"] == "Telescope"
    assert dto["setupType"] == "telescope"
    assert dto["setupText"] == "25 mm"
    assert dto["bestEyepiece"] == "25 mm"
    assert dto["barlow"] == "No"
    assert dto["setupOptions"][0]["role"] == "Consigliato"
    assert dto["setupOptions"][0]["detailLabel"] == "25 mm"
    assert "campo reale" in dto["explanation"]


def test_presenter_prefixes_profile_telescope_setup() -> None:
    service = EquipmentService()
    target = _object("messier-M51", "M51", "Galaxy", "8.4", "11 arcmin", 0.183, "General")
    candidates = service._ranked_candidates(
        target,
        Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson"),
        [Eyepiece("e25", "25 mm", 25, 52)],
        [],
    )

    dto = RecommendationPresenter().from_candidates(
        target,
        candidates,
        service._recommended_candidate(candidates),
        prefix_telescope=True,
    )

    assert dto["setupText"] == "Dobson 200 + 25 mm"
    assert dto["telescopeName"] == "Dobson 200"


def test_presenter_serializes_binocular_recommendation_without_telescope_placeholders() -> None:
    service = EquipmentService()
    target = _object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField")
    candidates = service._ranked_profile_candidates(
        target,
        [],
        [],
        [],
        [Binocular("canon", "Canon 15x50 IS All Weather", 15, 50, True)],
    )

    dto = RecommendationPresenter().from_candidates(target, candidates, service._recommended_candidate(candidates))

    assert dto["equipmentType"] == "Binocular"
    assert dto["setupType"] == "binocular"
    assert dto["setupText"] == "Canon 15×50 IS All Weather"
    assert dto["bestEyepiece"] == "Non richiesto"
    assert dto["suggestedPosition"] == ""
    assert dto["setupOptions"][0]["trueField"] == "n/d"
    assert "Oculare" not in dto["setupText"]
    assert "Barlow" not in dto["setupText"]
    assert "Binocolo stabilizzato" in dto["explanation"]


def test_presenter_serializes_naked_eye_fallback() -> None:
    target = _object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification")

    dto = RecommendationPresenter().naked_eye(target, EquipmentService.NAKED_EYE_ID)

    assert dto["equipmentType"] == "NakedEye"
    assert dto["setupType"] == "naked_eye"
    assert dto["setupText"] == "Serve almeno un binocolo o telescopio"
    assert dto["bestEyepiece"] == ""


def test_presenter_serializes_missing_eyepiece_fallback() -> None:
    target = _object("jupiter", "Giove", "Pianeta", "-2.0", "45 arcsec", 0.013, "HighMagnification")

    dto = RecommendationPresenter().missing_eyepieces(
        target,
        Telescope("scope", "Newton 150/750", 150, 750, "Newton", "manuale"),
    )

    assert dto["equipmentType"] == "Telescope"
    assert dto["setupText"] == "Aggiungi oculari per suggerimenti completi"
    assert dto["difficulty"] == "Limitata"
    assert dto["setupOptions"] == []


@pytest.mark.parametrize(
    ("object_id", "aperture_mm", "expected"),
    (
        ("jupiter", 100, "Facile"),
        ("mars", 100, "Media"),
        ("mercury", 100, "Difficile"),
        ("uranus", 100, "Media"),
        ("neptune", 100, "Difficile"),
        ("neptune", 150, "Media"),
        ("uranus", 220, "Facile"),
    ),
)
def test_planet_telescope_difficulty_respects_target_and_aperture(
    object_id: str,
    aperture_mm: int,
    expected: str,
) -> None:
    target = _object(object_id, object_id.title(), "Pianeta", "5.7", "4 arcsec", 0.002, "HighMagnification")
    telescope = Telescope("scope", "Scope", aperture_mm, 1000, "Reflector", "manuale")

    difficulty = RecommendationPresenter()._difficulty_for_object(target, telescope)

    assert difficulty == expected


def test_outer_planets_are_not_easy_with_binoculars() -> None:
    target = _object("neptune", "Nettuno", "Pianeta", "7.8", "2 arcsec", 0.001, "HighMagnification")

    difficulty = RecommendationPresenter()._difficulty_for_binocular(
        target,
        SimpleNamespace(score=90.0),
    )

    assert difficulty == "Difficile"


def test_mercury_naked_eye_is_realistic_but_difficult() -> None:
    target = _object("mercury", "Mercurio", "Pianeta", "-0.5", "8 arcsec", 0.002, "HighMagnification")

    dto = RecommendationPresenter().naked_eye(target, EquipmentService.NAKED_EYE_ID)

    assert dto["setupText"] == "Occhio nudo"
    assert dto["difficulty"] == "Difficile"


def test_supernova_remnant_is_not_inferred_as_naked_eye_target_from_integrated_magnitude() -> None:
    target = _object(
        "remnant-test",
        "Remnant",
        "Supernova remnant",
        "4.0",
        "3 deg",
        3.0,
        "WideField",
    )

    dto = RecommendationPresenter().naked_eye(target, EquipmentService.NAKED_EYE_ID)

    assert dto["setupText"] == "Serve almeno un binocolo o telescopio"
    assert dto["difficulty"] == "Non adatto a occhio nudo"


def test_presenter_disambiguates_same_eyepiece_label_across_telescopes() -> None:
    service = EquipmentService()
    target = _object(
        "messier-M17",
        "M17",
        "H II region nebula with cluster",
        "6.0",
        "11 arcmin",
        0.183,
        "General",
    )

    dto = service.suggest_for_profile(
        target,
        [
            Telescope("mak127", "Mak 127", 127, 1500, "Maksutov", "manuale"),
            Telescope("newton130", "Newton 130/650", 130, 650, "Newton", "manuale"),
        ],
        [
            Eyepiece(
                "hyperion-zoom",
                "Baader Hyperion Zoom 8-24 mm",
                24,
                60,
                "Zoom",
                8,
                24,
                (24, 20, 16, 12, 8),
            ),
            Eyepiece("e32", "32 mm", 32, 68),
            Eyepiece("e10", "10 mm", 10, 60),
            Eyepiece("e6", "6 mm", 6, 58),
        ],
        [Barlow("b2", "Barlow 2x", 2.0)],
        seeing=SeeingTransparency("Average", "Average", 55, 50, ""),
        sky_quality=SkyQuality(7, 4.7, 18.5, "SyntheticVIIRS", "Urban synthetic sky.", viirs_radiance=75.0),
        binoculars=[Binocular("b10x50", "Nikon Aculon A211", 10, 50)],
    )

    matching_options = [
        option
        for option in dto["setupOptions"]
        if option["detailLabel"] == "32 mm"
    ]
    display_labels = [option["displayLabel"] for option in dto["setupOptions"]]

    assert len(matching_options) == 2
    assert {option["displayLabel"] for option in matching_options} == {
        "Mak 127 + 32 mm",
        "Newton 130/650 + 32 mm",
    }
    assert len(display_labels) == len(set(display_labels))


def test_faint_extended_target_does_not_offer_an_extreme_visual_option() -> None:
    service = EquipmentService()
    target = _object(
        "caldwell-C3",
        "C3",
        "Spiral galaxy",
        "9.7",
        "21 × 7 arcmin",
        0.35,
        "General",
    )
    candidates = service._ranked_candidates(
        target,
        Telescope(
            "nexstar-6se",
            "Celestron NexStar 6SE",
            150,
            1500,
            "Schmidt-Cassegrain",
            "ALTAZ_GOTO",
        ),
        [
            Eyepiece(
                "zoom",
                "Zoom 8-24 mm",
                24,
                60,
                "Zoom",
                8,
                24,
                (24, 20, 16, 12, 8),
            ),
        ],
        [Barlow("barlow-2x", "Barlow 2x", 2.0)],
    )

    dto = RecommendationPresenter().from_candidates(
        target,
        candidates,
        service._recommended_candidate(candidates),
    )
    high_option = next(
        option
        for option in dto["setupOptions"]
        if option["roleCode"] == "high_magnification"
    )

    assert high_option["magnification"] == "125x"
    assert high_option["barlow"] == "No"
    assert high_option["exitPupil"] == "1,2 mm"
    assert high_option["trueField"] == "0,48°"


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
