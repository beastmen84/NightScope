"""Declare canonical filter classes and target-specific filter preferences."""

from __future__ import annotations

from astro_viewer.app.services.localization import tr


FILTER_CLASS_OPTIONS: tuple[tuple[str, str], ...] = (
    ("UHC", "UHC"),
    ("OIII", "OIII"),
    ("H_BETA", "H-beta"),
    ("CLS", tr("Riduzione inquinamento luminoso")),
    ("MOON_SKYGLOW", tr("Luna e contrasto")),
    ("ND", tr("Densità neutra")),
    ("POLARIZING", tr("Polarizzatore")),
    ("COLOR_YELLOW", tr("Filtro colorato (giallo)")),
    ("COLOR_ORANGE", tr("Filtro colorato (arancio)")),
    ("COLOR_RED", tr("Filtro colorato (rosso)")),
    ("COLOR_LIGHT_BLUE", tr("Filtro colorato (azzurro)")),
    ("COLOR_DARK_BLUE", tr("Filtro colorato (blu scuro)")),
    ("COLOR_GREEN", tr("Filtro colorato (verde)")),
    ("COLOR_LIGHT_GREEN", tr("Filtro colorato (verde chiaro)")),
    ("COLOR_VIOLET", tr("Filtro colorato (viola)")),
    ("CONTRAST", tr("Contrasto planetario")),
    ("CHROMATIC", tr("Correzione cromatica")),
    ("COMET", tr("Comete")),
)

FILTER_CLASS_LABELS = dict(FILTER_CLASS_OPTIONS)
FILTER_CLASS_CODES = frozenset(FILTER_CLASS_LABELS)


SOLAR_SYSTEM_FILTER_PREFERENCES = {
    "moon": ("POLARIZING", "ND", "COLOR_YELLOW"),
    "mercury": ("", "", "COLOR_RED"),
    "venus": ("POLARIZING", "ND", "COLOR_VIOLET"),
    "mars": ("CONTRAST", "MOON_SKYGLOW", "COLOR_RED"),
    "jupiter": ("CONTRAST", "MOON_SKYGLOW", "COLOR_LIGHT_BLUE"),
    "saturn": ("CONTRAST", "MOON_SKYGLOW", "COLOR_LIGHT_BLUE"),
    "uranus": ("", "", "COLOR_YELLOW"),
    "neptune": ("", "", "COLOR_YELLOW"),
}


TARGET_FILTER_CLASS_MINIMUM_APERTURE_MM = {
    ("uranus", "COLOR_YELLOW"): 280,
    ("neptune", "COLOR_YELLOW"): 280,
}
