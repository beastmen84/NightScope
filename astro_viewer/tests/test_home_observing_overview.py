from __future__ import annotations

from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import (
    ObservingSessionDecision,
    WeatherBlockingStatus,
    WeatherSummary,
)
from astro_viewer.app.services.home_observing_overview import HomeObservingOverviewService


def test_discouraged_session_stays_separate_from_category_diagnostics() -> None:
    payload = _service().build(
        weather=_weather(),
        seeing=_seeing(),
        sky_quality=_sky_quality(),
        moon=_moon("21%"),
        category_scores=AdvancedObservingScores(82, 58, "Buona", "Discreta", "NSOM categories"),
        session=ObservingSessionDecision(
            state="discouraged",
            title="Sessione sconsigliata",
            detail="Le condizioni previste rimangono sfavorevoli per tutta la notte.",
            description="Non è consigliabile preparare una sessione osservativa.",
        ),
        blocking=WeatherBlockingStatus(
            blocks_plan=True,
            show_warning=True,
            reason="rischio precipitazioni",
            detail="Rischio precipitazioni elevato.",
        ),
        suggested_window="23:00–02:00",
        wind_label="debole",
        category_source="nsom_category_diagnostic",
    )

    assert payload["session"]["state"] == "discouraged"
    assert payload["session"]["windowText"] == "Nessuna finestra consigliata"
    assert payload["weather"]["scoreValue"] == 42
    assert payload["planetary"]["label"] == "Buona"
    assert payload["deepSky"]["label"] == "Discreta"
    assert payload["planetary"]["source"] == "nsom_category_diagnostic"


def test_monitor_session_exposes_only_the_actionable_window() -> None:
    payload = _service().build(
        weather=_weather(),
        seeing=_seeing(),
        sky_quality=_sky_quality(),
        moon=_moon("45%"),
        category_scores=AdvancedObservingScores(70, 55, "Discreta", "Discreta", "NSOM categories"),
        session=ObservingSessionDecision(
            state="monitor",
            title="Sessione da monitorare",
            detail="Le condizioni attuali non sono ancora favorevoli.",
            description="È prevista una finestra osservativa promettente.",
            show_opportunity=True,
        ),
        blocking=WeatherBlockingStatus(
            blocks_plan=False,
            show_warning=True,
            reason="nuvolosità elevata",
            detail="Nuvolosità elevata.",
        ),
        suggested_window="01:00–03:00",
        wind_label="debole",
        category_source="nsom_category_diagnostic",
    )

    assert payload["session"]["hasWindow"] is True
    assert payload["session"]["windowLabel"] == "Possibile finestra"
    assert payload["session"]["windowText"] == "Possibile finestra: 01:00–03:00"
    assert payload["weather"]["windowText"] == payload["session"]["windowText"]


def test_moon_summary_describes_only_lunar_impact() -> None:
    payload = _service().build(
        weather=_weather(),
        seeing=_seeing(),
        sky_quality=_sky_quality(),
        moon=_moon("21%"),
        category_scores=AdvancedObservingScores(80, 60, "Buona", "Discreta", "NSOM categories"),
        session=ObservingSessionDecision(state="recommended"),
        blocking=WeatherBlockingStatus(blocks_plan=False, show_warning=False),
        suggested_window="22:00–01:00",
        wind_label="debole",
        category_source="nsom_category_diagnostic",
    )

    assert payload["moon"]["impact"] == "low"
    assert payload["moon"]["impactLabel"] == "Impatto lunare basso"
    assert payload["moon"]["summary"] == "Luna poco luminosa: impatto ridotto sul cielo profondo."
    assert "Cielo favorevole" not in payload["moon"]["summary"]


def test_missing_weather_has_an_explicit_unavailable_state() -> None:
    payload = _service().build(
        weather=None,
        seeing=None,
        sky_quality=None,
        moon=None,
        category_scores=None,
        session=ObservingSessionDecision(state="recommended"),
        blocking=WeatherBlockingStatus(blocks_plan=False, show_warning=False),
        suggested_window="",
        wind_label="n/d",
        category_source="legacy_category_fallback",
    )

    assert payload["session"]["state"] == "unavailable"
    assert payload["weather"]["scoreLabel"] == "n/d"
    assert payload["planetary"]["label"] == "n/d"
    assert payload["deepSky"]["label"] == "n/d"


def _service() -> HomeObservingOverviewService:
    return HomeObservingOverviewService()


def _weather() -> WeatherSummary:
    return WeatherSummary(
        score="Scarsa",
        score_value=42,
        explanation="Nuvolosità moderata, rischio precipitazioni, vento debole.",
        cloud_cover=40,
        precipitation_probability=72,
        wind_kmh=6,
        humidity=70,
        temperature_c=14.0,
        alert="Qualità osservativa stanotte: 42/100, scarsa.",
    )


def _seeing() -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Excellent",
        transparency="Poor",
        seeing_score=88,
        transparency_score=34,
        explanation="Test seeing/transparency.",
    )


def _sky_quality() -> SkyQuality:
    return SkyQuality(
        bortle_class=7,
        limiting_magnitude=4.6,
        sky_brightness=18.8,
        source="NASA Black Marble VNP46A3",
        description="Urban Sky",
        confidence="high",
        viirs_radiance=55.59,
        viirs_observation_count=18,
    )


def _moon(illumination: str) -> MoonSummary:
    return MoonSummary(
        phase="Calante",
        illumination=illumination,
        rise_time="01:45",
        set_time="14:44",
        best_note="Legacy global note",
        image="resources/images/moon.svg",
    )
