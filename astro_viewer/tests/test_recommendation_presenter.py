from __future__ import annotations

from astro_viewer.app.models.equipment import Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
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
