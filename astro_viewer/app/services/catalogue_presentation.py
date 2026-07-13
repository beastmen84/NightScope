from __future__ import annotations

from astro_viewer.app.services.localization import presentation_text, tr


_OBJECT_TYPE_LABELS = {
    "asterism": tr("Asterismo"),
    "barred spiral galaxy": tr("Galassia spirale barrata"),
    "diffuse nebula": tr("Nebulosa diffusa"),
    "dark nebula": tr("Nebulosa oscura"),
    "dwarf elliptical galaxy": tr("Galassia ellittica nana"),
    "elliptical galaxy": tr("Galassia ellittica"),
    "galaxy": tr("Galassia"),
    "globular cluster": tr("Ammasso globulare"),
    "h ii region nebula": tr("Nebulosa H II"),
    "h ii region nebula (part of the orion nebula)": tr("Nebulosa H II di Orione"),
    "h ii region nebula with cluster": tr("Nebulosa H II con ammasso"),
    "irregular galaxy": tr("Galassia irregolare"),
    "lenticular galaxy": tr("Galassia lenticolare"),
    "milky way star cloud": tr("Nube stellare della Via Lattea"),
    "nebula": tr("Nebulosa"),
    "nebula with cluster": tr("Nebulosa con ammasso"),
    "open cluster": tr("Ammasso aperto"),
    "optical double": tr("Doppia ottica"),
    "planet": tr("Pianeta"),
    "pianeta": tr("Pianeta"),
    "planetary nebula": tr("Nebulosa planetaria"),
    "peculiar galaxy": tr("Galassia peculiare"),
    "seyfert galaxy": tr("Galassia di Seyfert"),
    "spiral galaxy": tr("Galassia spirale"),
    "starburst galaxy": tr("Galassia starburst"),
    "supernova remnant": tr("Resto di supernova"),
}

_OBSERVATION_TYPE_LABELS = {
    "general": tr("Generale"),
    "highmagnification": tr("Alto ingrandimento"),
    "widefield": tr("Campo largo"),
}


def catalogue_object_type_label(value: str) -> str:
    clean = value.strip()
    return _OBJECT_TYPE_LABELS.get(clean.casefold(), clean)


def catalogue_observation_type_label(value: str) -> str:
    clean = value.strip()
    return _OBSERVATION_TYPE_LABELS.get(clean.casefold(), clean)


def catalogue_display_name(designation: str, name: object) -> str:
    """Composes a localized catalogue label without storing derived translations."""

    clean_designation = designation.strip()
    clean_name = presentation_text(name, strip=True)
    if not clean_name or clean_name.casefold() == clean_designation.casefold():
        return clean_designation
    return tr(
        "{designation} {name}",
        designation=clean_designation,
        name=clean_name,
    )
