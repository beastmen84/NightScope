from __future__ import annotations

from astro_viewer.app.services.localization import tr


MOUNT_TYPE_OPTIONS = (
    ("OTA", tr("Solo tubo ottico (OTA)")),
    ("MANUAL_UNSPECIFIED", tr("Montatura manuale non specificata")),
    ("ALTAZ_MANUAL", tr("Altazimutale manuale")),
    ("ALTAZ_GOTO", tr("Altazimutale GoTo")),
    ("ALTAZ_PUSHTO", tr("Altazimutale PushTo")),
    ("EQUATORIAL_MANUAL", tr("Equatoriale manuale")),
    ("EQUATORIAL_TRACKING", tr("Equatoriale motorizzata")),
    ("FORK_GOTO", tr("Forcella GoTo")),
    ("DOBSONIAN_MANUAL", tr("Dobson manuale")),
    ("DOBSONIAN_GOTO", tr("Dobson GoTo")),
    ("DOBSONIAN_PUSHTO", tr("Dobson PushTo")),
    ("OTHER", tr("Altra montatura")),
)
MOUNT_TYPE_LABELS = dict(MOUNT_TYPE_OPTIONS)

_MOUNT_TYPE_ALIASES = {
    "ota": "OTA",
    "manuale": "MANUAL_UNSPECIFIED",
    "altazimutale": "ALTAZ_MANUAL",
    "goto altazimutale": "ALTAZ_GOTO",
    "altazimutale pushto": "ALTAZ_PUSHTO",
    "equatoriale": "EQUATORIAL_MANUAL",
    "equatoriale cg-4": "EQUATORIAL_MANUAL",
    "goto forcella": "FORK_GOTO",
    "dobson": "DOBSONIAN_MANUAL",
    "dobson tabletop": "DOBSONIAN_MANUAL",
    "dobson collassabile": "DOBSONIAN_MANUAL",
    "dobson goto": "DOBSONIAN_GOTO",
    "dobson pushto": "DOBSONIAN_PUSHTO",
}


def canonical_mount_type(value: object, *, preserve_unknown: bool = True) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    upper_value = raw_value.upper()
    if upper_value in MOUNT_TYPE_LABELS:
        return upper_value
    canonical = _MOUNT_TYPE_ALIASES.get(raw_value.casefold())
    if canonical:
        return canonical
    return raw_value if preserve_unknown else ""


def mount_type_label(value: object) -> object:
    canonical = canonical_mount_type(value)
    return MOUNT_TYPE_LABELS.get(canonical, canonical)


def mount_tracking_capability(value: object) -> float:
    """Preserve the existing visual score while exposing normalized mount codes."""

    canonical = canonical_mount_type(value)
    if canonical in {
        "ALTAZ_GOTO",
        "EQUATORIAL_MANUAL",
        "EQUATORIAL_TRACKING",
        "FORK_GOTO",
        "DOBSONIAN_GOTO",
    }:
        return 0.8
    if canonical in {
        "MANUAL_UNSPECIFIED",
        "ALTAZ_MANUAL",
        "ALTAZ_PUSHTO",
        "DOBSONIAN_MANUAL",
        "DOBSONIAN_PUSHTO",
    }:
        return 0.2
    if canonical in {"OTA", "OTHER"}:
        return 0.4

    text = str(value or "").casefold()
    if any(
        token in text
        for token in ("goto", "go-to", "computer", "eq", "tracking", "motoriz")
    ):
        return 0.8
    if any(token in text for token in ("dob", "altaz", "manual")):
        return 0.2
    return 0.4


ASTRONOMY_CAMERA_CLASS_OPTIONS = (
    ("DEEP_SKY", tr("Cielo profondo")),
    ("PLANETARY", tr("Planetaria, lunare e solare")),
    ("ALL_ROUND", tr("Polivalente")),
)
ASTRONOMY_CAMERA_CLASS_LABELS = dict(ASTRONOMY_CAMERA_CLASS_OPTIONS)

SENSOR_TECHNOLOGY_OPTIONS = (
    ("CMOS", "CMOS"),
    ("CCD", "CCD"),
)
SENSOR_TECHNOLOGY_LABELS = dict(SENSOR_TECHNOLOGY_OPTIONS)

SENSOR_COLOR_MODE_OPTIONS = (
    ("COLOR", tr("Colore")),
    ("MONO", tr("Monocromatica")),
)
SENSOR_COLOR_MODE_LABELS = dict(SENSOR_COLOR_MODE_OPTIONS)

SENSOR_SHUTTER_OPTIONS = (
    ("ROLLING", tr("Rolling shutter")),
    ("GLOBAL", tr("Global shutter")),
)
SENSOR_SHUTTER_LABELS = dict(SENSOR_SHUTTER_OPTIONS)

CAMERA_BODY_TYPE_OPTIONS = (
    ("MIRRORLESS", "Mirrorless"),
    ("DSLR", "DSLR"),
)
CAMERA_BODY_TYPE_LABELS = dict(CAMERA_BODY_TYPE_OPTIONS)

CAMERA_SENSOR_FORMAT_OPTIONS = (
    ("FULL_FRAME", "Full frame"),
    ("APS_C", "APS-C"),
    ("MICRO_FOUR_THIRDS", "Micro Four Thirds"),
)
CAMERA_SENSOR_FORMAT_LABELS = dict(CAMERA_SENSOR_FORMAT_OPTIONS)
