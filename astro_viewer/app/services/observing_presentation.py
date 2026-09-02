"""Build observing status, timing, and Moon presentation without controller state."""

from __future__ import annotations

import re
from datetime import datetime

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.astronomy.skyfield_engine import (
    DEEP_SKY_USEFUL_ALTITUDE_DEG,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.localization import format_number, tr
from astro_viewer.app.services.observing_time import home_time_period_code


class ObservingPresentationService:
    """Builds observing status and explanation text without controller state."""

    def status_data(
        self,
        item: CelestialObject,
        *,
        catalogue_name: str | None,
        now: datetime,
        night_window: ObservingNightWindow,
        monthly_visibility_blocked: bool,
        useful_datetime: datetime | None,
        window: str,
        altitude_threshold: float,
    ) -> tuple[str, str, str]:
        if catalogue_name is not None:
            return (
                "catalogue",
                tr("Catalogo {catalogue}", catalogue=catalogue_name),
                tr("Scheda informativa caricata dal catalogo locale."),
            )

        current_altitude = parse_degrees(item.current_altitude)
        is_observing_time = night_window.contains(now)
        observable_now = item.observable_now
        if observable_now is None:
            observable_now = bool(
                is_observing_time
                and current_altitude is not None
                and current_altitude >= altitude_threshold
            )
        if monthly_visibility_blocked:
            if current_altitude is not None and current_altitude > 0:
                return (
                    "above_horizon",
                    tr("Sopra l'orizzonte"),
                    tr(
                        "Sopra l'orizzonte, ma non utile per l'osservazione "
                        "questo mese."
                    ),
                )
            if useful_datetime:
                return (
                    "limited",
                    tr("Finestra marginale"),
                    tr(
                        "Finestra marginale: l'oggetto non raggiunge la "
                        "visibilità utile mensile."
                    ),
                )
            return (
                "limited",
                tr("Non utile questo mese"),
                tr(
                    "Non raggiunge una finestra utile questo mese secondo il "
                    "criterio di visibilità mensile."
                ),
            )
        if observable_now:
            altitude = (
                tr("{value}°", value=format_number(current_altitude))
                if current_altitude is not None
                else tr("quota utile")
            )
            return (
                "observable_now",
                tr("Osservabile ora"),
                tr(
                    "Attualmente a {altitude}. Finestra utile: {window}.",
                    altitude=altitude,
                    window=window,
                ),
            )
        if current_altitude is not None and current_altitude > 0 and not is_observing_time:
            return (
                "above_horizon",
                tr("Sopra l'orizzonte"),
                tr(
                    "Attualmente a {altitude}°, ma fuori dalla notte "
                    "osservativa. Finestra utile: {window}.",
                    altitude=format_number(current_altitude),
                    window=window,
                ),
            )
        if useful_datetime:
            if home_time_period_code(useful_datetime, night_window) == "before_dawn":
                return (
                    "later",
                    tr("Meglio prima dell'alba"),
                    tr(
                        "Attualmente sotto la soglia utile. Finestra prima "
                        "dell'alba: {window}.",
                        window=window,
                    ),
                )
            if useful_datetime > now:
                return (
                    "later",
                    tr("Meglio più tardi"),
                    tr(
                        "Attualmente sotto la soglia utile. Finestra più "
                        "tardi: {window}.",
                        window=window,
                    ),
                )
        if current_altitude is not None and current_altitude > 0:
            return (
                "limited",
                tr("Troppo basso ora"),
                tr(
                    "Attualmente a {altitude}°, sotto la soglia utile di "
                    "{threshold}°. Finestra utile: {window}.",
                    altitude=format_number(current_altitude),
                    threshold=format_number(altitude_threshold),
                    window=window,
                ),
            )
        if useful_datetime:
            return (
                "unavailable",
                tr("Finestra conclusa"),
                tr(
                    "La finestra utile di questa notte era {window}.",
                    window=window,
                ),
            )
        if item.visible:
            return (
                "later",
                tr("Finestra utile"),
                tr(
                    "Finestra osservativa: {window}.",
                    window=item.observing_window,
                ),
            )
        return (
            "unavailable",
            tr("Non osservabile"),
            tr("Nessuna finestra notturna utile per questa posizione."),
        )

    def reasons(
        self,
        item: CelestialObject,
        *,
        is_catalogue_detail: bool,
        moon: MoonSummary | None,
        seeing_transparency: SeeingTransparency | None,
        sky_quality: SkyQuality | None,
    ) -> list[str]:
        if is_catalogue_detail:
            return []
        reasons = []
        max_altitude = parse_degrees(item.max_altitude)
        if max_altitude is not None and max_altitude > 0:
            reasons.append(altitude_reason(max_altitude))
        if item.time_above_horizon and item.time_above_horizon not in {"n/d", "0 h"}:
            reasons.append(
                tr(
                    "Finestra utile sopra soglia: {duration}.",
                    duration=item.time_above_horizon,
                )
            )
        if item.id == "moon" and moon:
            reasons.append(
                tr(
                    "Fase lunare: {phase}, illuminazione {illumination}.",
                    phase=moon.phase,
                    illumination=moon.illumination,
                )
            )
        elif seeing_transparency and item.object_type == "Pianeta":
            seeing = localized_seeing(seeing_transparency.seeing)
            reasons.append(
                tr(
                    "Seeing previsto: {seeing}. Adatto a valutare dettagli "
                    "planetari.",
                    seeing=seeing,
                )
            )
        elif sky_quality and item.object_type != "Pianeta":
            reasons.append(sky_quality_reason(item, sky_quality))
        return reasons[:4]

    def setup_reason(self, item: CelestialObject) -> str:
        return setup_reason(item)


def is_planetary_or_lunar_target(item: CelestialObject) -> bool:
    return item.id in {
        "sun",
        "moon",
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
    } or item.object_type == "Pianeta"


def observing_altitude_threshold(item: CelestialObject) -> float:
    return 8.0 if is_planetary_or_lunar_target(item) else DEEP_SKY_USEFUL_ALTITUDE_DEG


def altitude_reason(max_altitude: float) -> str:
    altitude = format_number(max_altitude)
    if max_altitude >= 65:
        return tr(
            "Culmina molto alto ({altitude}°): meno atmosfera e immagine più stabile.",
            altitude=altitude,
        )
    if max_altitude >= 35:
        return tr(
            "Raggiunge una buona altezza ({altitude}°): osservazione realistica.",
            altitude=altitude,
        )
    if max_altitude >= 15:
        return tr(
            "Resta basso ({altitude}°): serve orizzonte libero e cielo stabile.",
            altitude=altitude,
        )
    return tr(
        "Altezza massima critica ({altitude}°): oggetto difficile da sfruttare.",
        altitude=altitude,
    )


def localized_seeing(value: str) -> str:
    labels = {
        "Excellent": tr("Eccellente"),
        "Good": tr("Buono"),
        "Average": tr("Discreto"),
        "Poor": tr("Scarso"),
    }
    return labels.get(value, value or tr("n/d"))


def sky_quality_reason(item: CelestialObject, sky_quality: SkyQuality) -> str:
    bortle = sky_quality.bortle_class
    difficulty = (
        item.difficulty
        if item.difficulty and item.difficulty != "n/d"
        else "da valutare"
    )
    if difficulty == "Facile":
        return tr(
            "Cielo Bortle {bortle}: oggetto ancora gestibile, difficoltà "
            "stimata facile.",
            bortle=bortle,
        )
    if difficulty == "Media":
        return tr(
            "Cielo Bortle {bortle}: richiede adattamento al buio, difficoltà media.",
            bortle=bortle,
        )
    if difficulty == "Difficile":
        return tr(
            "Cielo Bortle {bortle}: oggetto penalizzato, meglio trasparenza "
            "alta e luci schermate.",
            bortle=bortle,
        )
    return tr(
        "Cielo Bortle {bortle}: difficoltà stimata {difficulty}.",
        bortle=bortle,
        difficulty=(
            tr("da valutare") if difficulty == "da valutare" else difficulty
        ),
    )


def setup_reason(item: CelestialObject) -> str:
    if not item.recommended_setup:
        return ""
    option = recommended_setup_option(item)
    magnification = option.get("magnification", "") if option else ""
    true_field = option.get("trueField", "") if option else ""
    exit_pupil = option.get("exitPupil", "") if option else ""
    barlow = option.get("barlow", "") if option else item.barlow
    lower_type = item.object_type.lower()
    if option.get("equipmentType") == "Binocular":
        if (
            "open" in lower_type
            or "ammasso aperto" in lower_type
            or "star cloud" in lower_type
        ):
            return tr(
                "{magnification} e pupilla {exit_pupil}: campo ampio e visione "
                "naturale dell'ammasso.",
                magnification=magnification,
                exit_pupil=exit_pupil,
            )
        if "galaxy" in lower_type or "galassia" in lower_type:
            return tr(
                "{magnification} e pupilla {exit_pupil}: adatto a oggetti "
                "molto estesi e a basso contrasto.",
                magnification=magnification,
                exit_pupil=exit_pupil,
            )
        if "nebula" in lower_type or "nebul" in lower_type:
            return tr(
                "{magnification} e pupilla {exit_pupil}: utile per individuare "
                "l'oggetto senza stringere troppo il campo.",
                magnification=magnification,
                exit_pupil=exit_pupil,
            )
        return item.equipment_explanation or tr(
            "{magnification} e pupilla {exit_pupil}: configurazione binoculare "
            "a basso ingrandimento.",
            magnification=magnification,
            exit_pupil=exit_pupil,
        )
    if magnification and exit_pupil:
        if item.id == "moon":
            return tr(
                "{magnification} e pupilla {exit_pupil}: dettaglio lunare "
                "leggibile senza spingere troppo l'immagine.",
                magnification=magnification,
                exit_pupil=exit_pupil,
            )
        if item.object_type == "Pianeta":
            return tr(
                "{magnification} e pupilla {exit_pupil}: compromesso tra "
                "dettaglio planetario e seeing previsto.",
                magnification=magnification,
                exit_pupil=exit_pupil,
            )
        if (
            "open" in lower_type
            or "ammasso aperto" in lower_type
            or "star cloud" in lower_type
        ):
            return tr(
                "Campo reale {true_field}: mantiene l'oggetto nel suo contesto "
                "stellare.",
                true_field=true_field,
            )
        if "globular" in lower_type or "ammasso globulare" in lower_type:
            return tr(
                "{magnification} e pupilla {exit_pupil}: aiuta a separare il "
                "nucleo senza scurire troppo.",
                magnification=magnification,
                exit_pupil=exit_pupil,
            )
        if "galaxy" in lower_type or "galassia" in lower_type:
            return tr(
                "Pupilla {exit_pupil} e campo {true_field}: privilegia "
                "contrasto e orientamento della galassia.",
                exit_pupil=exit_pupil,
                true_field=true_field,
            )
        if "nebula" in lower_type or "nebul" in lower_type:
            return tr(
                "Pupilla {exit_pupil} e campo {true_field}: equilibrio utile "
                "per oggetti diffusi.",
                exit_pupil=exit_pupil,
                true_field=true_field,
            )
    if item.equipment_explanation:
        return item.equipment_explanation
    if barlow and barlow != "No":
        return tr("Barlow inclusa per raggiungere un ingrandimento più utile.")
    return tr(
        "Configurazione scelta in base al profilo attivo e al tipo di oggetto."
    )


def recommended_setup_option(item: CelestialObject) -> dict:
    for option in item.setup_options:
        if option.get("roleCode") == "recommended":
            return option
    return item.setup_options[0] if item.setup_options else {}


def recommendation_setup_type(suggestion: dict) -> str:
    setup_type = suggestion.get("setupType", "")
    if setup_type:
        return setup_type
    equipment_type = suggestion.get("equipmentType", "")
    if equipment_type == "Binocular":
        return "binocular"
    if equipment_type == "Telescope":
        return "telescope"
    for option in suggestion.get("setupOptions", []):
        if option.get("roleCode") == "recommended":
            option_type = option.get("equipmentType", "")
            if option_type == "Binocular":
                return "binocular"
            if option_type == "Telescope":
                return "telescope"
    return ""


def moon_cycle_fraction(phase_angle: float) -> float:
    return round((phase_angle % 360.0) / 360.0, 4)


def moon_cycle_day_label(phase_angle: float) -> str:
    cycle_day = moon_cycle_fraction(phase_angle) * 29.53
    return tr(
        "Giorno {day} di {cycle}",
        day=format_number(cycle_day, decimals=1),
        cycle=format_number(29.5, decimals=1),
    )


def parse_degrees(value: str) -> float | None:
    match = re.search(r"-?\d+(?:[\.,]\d+)?", value or "")
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None
