from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject

from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import ObservingCategoryScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import (
    ObservingSessionDecision,
    WeatherBlockingStatus,
    WeatherSummary,
)
from astro_viewer.app.services.home_observing_overview import (
    HomeObservingOverviewService,
    bortle_observing_warning,
)
from astro_viewer.app.viewmodels.app_controller import AppController


HOME_PAGE = Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "HomePage.qml"
GLASS_CARD = Path(__file__).resolve().parents[1] / "app" / "ui" / "components" / "GlassCard.qml"


def test_discouraged_session_stays_separate_from_category_diagnostics() -> None:
    payload = _service().build(
        location_available=True,
        location_pending=False,
        weather=_weather(),
        weather_available=True,
        seeing=_seeing(),
        sky_quality=_sky_quality(),
        moon=_moon("21%"),
        category_scores=ObservingCategoryScores(82, 58, "Buona", "Discreta", "NSOM categories"),
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
    assert payload["deepSky"]["secondaryMetric"] == "Bortle 7 - transizione suburbana-urbana"
    assert payload["planetary"]["source"] == "nsom_category_diagnostic"


def test_bortle_warning_uses_the_same_classification_as_the_upper_home() -> None:
    assert bortle_observing_warning(7) == (
        "Transizione suburbana-urbana: privilegiare oggetti brillanti e pianeti."
    )
    assert bortle_observing_warning(8) == (
        "Cielo urbano: oggetti cielo profondo limitati. Preferire ammassi aperti, pianeti e Luna."
    )


def test_app_controller_exposes_the_shared_bortle_warning() -> None:
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._sky_quality = _sky_quality()

    assert controller.skyQualityWarning == (
        "Transizione suburbana-urbana: privilegiare oggetti brillanti e pianeti."
    )


def test_monitor_session_exposes_only_the_actionable_window() -> None:
    payload = _service().build(
        location_available=True,
        location_pending=False,
        weather=_weather(),
        weather_available=True,
        seeing=_seeing(),
        sky_quality=_sky_quality(),
        moon=_moon("45%"),
        category_scores=ObservingCategoryScores(70, 55, "Discreta", "Discreta", "NSOM categories"),
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
        location_available=True,
        location_pending=False,
        weather=_weather(),
        weather_available=True,
        seeing=_seeing(),
        sky_quality=_sky_quality(),
        moon=_moon("21%"),
        category_scores=ObservingCategoryScores(80, 60, "Buona", "Discreta", "NSOM categories"),
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
        location_available=True,
        location_pending=False,
        weather=None,
        weather_available=False,
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
    assert "posizione" not in payload["session"]["description"].lower()
    assert payload["weather"]["available"] is False
    assert payload["weather"]["scoreValue"] is None
    assert payload["weather"]["scoreLabel"] == "n/d"
    assert payload["planetary"]["label"] == "n/d"
    assert payload["deepSky"]["label"] == "n/d"
    assert payload["planetary"]["hint"] == "Dati atmosferici non disponibili"
    assert payload["deepSky"]["hint"] == "Dati del cielo non disponibili"


def test_placeholder_values_stay_unavailable_without_provider_data() -> None:
    payload = _service().build(
        location_available=True,
        location_pending=False,
        weather=_weather(),
        weather_available=False,
        seeing=_seeing(),
        sky_quality=_sky_quality(),
        moon=_moon("n/d"),
        category_scores=ObservingCategoryScores(0, 0, "n/d", "n/d", "No data"),
        session=ObservingSessionDecision(state="recommended"),
        blocking=WeatherBlockingStatus(blocks_plan=False, show_warning=False),
        suggested_window="",
        wind_label="n/d",
        category_source="legacy_category_fallback",
    )

    assert payload["session"]["state"] == "unavailable"
    assert payload["weather"]["available"] is False
    assert payload["weather"]["scoreLabel"] == "n/d"
    assert payload["moon"]["impact"] == "unavailable"


def test_pending_location_has_coherent_transient_copy() -> None:
    payload = _service().build(
        location_available=False,
        location_pending=True,
        weather=None,
        weather_available=False,
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

    assert payload["session"]["state"] == "pending"
    assert payload["session"]["badge"] == "In attesa"
    assert payload["weather"]["state"] == "pending"
    assert payload["weather"]["badge"] == "In attesa"
    assert payload["planetary"]["state"] == "pending"
    assert payload["planetary"]["hint"] == "Calcolo dopo il rilevamento"
    assert payload["deepSky"]["state"] == "pending"
    assert payload["deepSky"]["hint"] == "Calcolo dopo il rilevamento"
    assert payload["moon"]["impact"] == "pending"


def test_missing_location_does_not_claim_favourable_conditions() -> None:
    payload = _service().build(
        location_available=False,
        location_pending=False,
        weather=_weather(),
        weather_available=True,
        seeing=_seeing(),
        sky_quality=_sky_quality(),
        moon=_moon("21%"),
        category_scores=ObservingCategoryScores(82, 58, "Buona", "Discreta", "NSOM categories"),
        session=ObservingSessionDecision(state="recommended"),
        blocking=WeatherBlockingStatus(blocks_plan=False, show_warning=False),
        suggested_window="23:00–02:00",
        wind_label="debole",
        category_source="nsom_category_diagnostic",
    )

    assert payload["session"]["state"] == "unavailable"
    assert payload["weather"]["available"] is False
    assert payload["planetary"]["hint"] == "Configura una località"
    assert payload["deepSky"]["hint"] == "Configura una località"
    assert "potenziale" not in payload["deepSky"]["hint"].lower()


def test_upper_home_cards_use_the_overview_contract_without_category_scores() -> None:
    qml = HOME_PAGE.read_text(encoding="utf-8")
    glass_card = GLASS_CARD.read_text(encoding="utf-8")

    assert "controller.homeObservingOverview" in qml
    assert 'title: qsTr("Sessione di stasera")' in qml
    assert 'title: qsTr("Condizioni planetarie")' in qml
    assert 'title: qsTr("Condizioni del cielo profondo")' in qml
    assert "root.weatherOverview.badge" in qml
    assert "root.moonOverview.summary" in qml
    assert 'title: qsTr("Qualità osservativa")' not in qml
    assert 'title: qsTr("Punteggio planetario")' not in qml
    assert 'title: qsTr("Punteggio cielo profondo")' not in qml
    assert "controller.advancedScores.planetaryScore" not in qml
    assert "controller.advancedScores.deepSkyScore" not in qml
    assert "function observingLimitFactor" not in qml
    assert "function moonImpactHint" not in qml
    assert qml.count("subtitleWrap: true") >= 4
    assert 'root.planetaryOverview.state === "pending"' in qml
    assert 'root.deepSkyOverview.state === "pending"' in qml
    assert 'root.weatherOverview.state === "pending"' in qml
    assert "property bool subtitleWrap: false" in glass_card
    assert "wrapMode: root.subtitleWrap ? Text.WordWrap : Text.NoWrap" in glass_card
    assert "maximumLineCount: root.subtitleWrap ? 2 : 1" in glass_card


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
        image="resources/images/solar_system/moon.jpg",
    )
