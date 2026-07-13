from __future__ import annotations


FILTER_CLASS_OPTIONS: tuple[tuple[str, str], ...] = (
    ("UHC", "UHC"),
    ("OIII", "OIII"),
    ("H_BETA", "H-beta"),
    ("CLS", "Riduzione inquinamento luminoso"),
    ("MOON_SKYGLOW", "Luna e contrasto"),
    ("ND", "Densità neutra"),
    ("POLARIZING", "Polarizzatore"),
    ("COLOR_YELLOW", "Colorato (giallo)"),
    ("COLOR_ORANGE", "Colorato (arancio)"),
    ("COLOR_RED", "Colorato (rosso)"),
    ("COLOR_LIGHT_BLUE", "Colorato (azzurro)"),
    ("COLOR_DARK_BLUE", "Colorato (blu scuro)"),
    ("COLOR_GREEN", "Colorato (verde)"),
    ("COLOR_LIGHT_GREEN", "Colorato (verde chiaro)"),
    ("COLOR_VIOLET", "Colorato (viola)"),
    ("CONTRAST", "Contrasto planetario"),
    ("CHROMATIC", "Correzione cromatica"),
    ("COMET", "Comete"),
)

FILTER_CLASS_LABELS = dict(FILTER_CLASS_OPTIONS)
FILTER_CLASS_LABELS["COLOR_UNSPECIFIED"] = "Colorato (da riclassificare)"
FILTER_CLASS_CODES = frozenset(FILTER_CLASS_LABELS)


SOLAR_SYSTEM_FILTER_PREFERENCES = {
    "moon": ("POLARIZING", "ND", "COLOR_YELLOW"),
    "mercury": ("", "", "COLOR_RED"),
    "venus": ("POLARIZING", "ND", "COLOR_VIOLET"),
    "mars": ("CONTRAST", "MOON_SKYGLOW", "COLOR_RED"),
    "jupiter": ("CONTRAST", "MOON_SKYGLOW", "COLOR_LIGHT_BLUE"),
    "saturn": ("CONTRAST", "MOON_SKYGLOW", "COLOR_LIGHT_BLUE"),
}
