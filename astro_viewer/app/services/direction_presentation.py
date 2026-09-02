"""Map canonical compass direction codes to localized presentation labels."""

from __future__ import annotations

from astro_viewer.app.services.localization import tr


_DIRECTION_LABELS = {
    "north": tr("Nord"),
    "north_east": tr("Nord-Est"),
    "east": tr("Est"),
    "south_east": tr("Sud-Est"),
    "south": tr("Sud"),
    "south_west": tr("Sud-Ovest"),
    "west": tr("Ovest"),
    "north_west": tr("Nord-Ovest"),
}

_CANONICAL_CODES = {
    "nord": "north",
    "nord-est": "north_east",
    "est": "east",
    "sud-est": "south_east",
    "sud": "south",
    "sud-ovest": "south_west",
    "ovest": "west",
    "nord-ovest": "north_west",
}


def direction_code(value: str) -> str:
    normalized = (value or "").strip().casefold().replace("_", "-")
    return _CANONICAL_CODES.get(normalized, "")


def direction_label(value_or_code: str) -> str:
    code = value_or_code if value_or_code in _DIRECTION_LABELS else direction_code(value_or_code)
    return _DIRECTION_LABELS.get(code, value_or_code or tr("n/d"))
