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

_CONSTELLATION_LABELS = {
    "Andromeda": tr("Andromeda"),
    "Apus": tr("Uccello del Paradiso"),
    "Aquarius": tr("Acquario"),
    "Ara": tr("Altare"),
    "Auriga": tr("Auriga"),
    "Bootes": tr("Boote"),
    "Camelopardalis": tr("Giraffa"),
    "Cancer": tr("Cancro"),
    "Canes Venatici": tr("Cani da Caccia"),
    "Canis Major": tr("Cane Maggiore"),
    "Capricornus": tr("Capricorno"),
    "Carina": tr("Carena"),
    "Cassiopeia": tr("Cassiopea"),
    "Centaurus": tr("Centauro"),
    "Cepheus": tr("Cefeo"),
    "Cetus": tr("Balena"),
    "Chamaeleon": tr("Camaleonte"),
    "Circinus": tr("Compasso"),
    "Columba": tr("Colomba"),
    "Coma Berenices": tr("Chioma di Berenice"),
    "Corona Australis": tr("Corona Australe"),
    "Corvus": tr("Corvo"),
    "Crux": tr("Croce del Sud"),
    "Cygnus": tr("Cigno"),
    "Delphinus": tr("Delfino"),
    "Dorado": tr("Dorado"),
    "Draco": tr("Drago"),
    "Fornax": tr("Fornace"),
    "Gemini": tr("Gemelli"),
    "Hercules": tr("Ercole"),
    "Horologium": tr("Orologio"),
    "Hydra": tr("Idra"),
    "Lacerta": tr("Lucertola"),
    "Leo": tr("Leone"),
    "Lepus": tr("Lepre"),
    "Lynx": tr("Lince"),
    "Lyra": tr("Lira"),
    "Monoceros": tr("Unicorno"),
    "Musca": tr("Mosca"),
    "Norma": tr("Regolo"),
    "Ophiuchus": tr("Ofiuco"),
    "Orion": tr("Orione"),
    "Pavo": tr("Pavone"),
    "Pegasus": tr("Pegaso"),
    "Perseus": tr("Perseo"),
    "Pisces": tr("Pesci"),
    "Puppis": tr("Poppa"),
    "Sagitta": tr("Freccia"),
    "Sagittarius": tr("Sagittario"),
    "Scorpius": tr("Scorpione"),
    "Sculptor": tr("Scultore"),
    "Scutum": tr("Scudo"),
    "Serpens": tr("Serpente"),
    "Sextans": tr("Sestante"),
    "Taurus": tr("Toro"),
    "Triangulum": tr("Triangolo"),
    "Triangulum Australe": tr("Triangolo Australe"),
    "Tucana": tr("Tucano"),
    "Ursa Major": tr("Orsa Maggiore"),
    "Vela": tr("Vele"),
    "Virgo": tr("Vergine"),
    "Vulpecula": tr("Volpetta"),
}


def catalogue_object_type_label(value: str) -> str:
    clean = value.strip()
    return _OBJECT_TYPE_LABELS.get(clean.casefold(), clean)


def catalogue_observation_type_label(value: str) -> str:
    clean = value.strip()
    return _OBSERVATION_TYPE_LABELS.get(clean.casefold(), clean)


def catalogue_constellation_label(value: str) -> str:
    """Localizes a canonical constellation name for presentation only."""

    clean = value.strip()
    return _CONSTELLATION_LABELS.get(clean, clean)


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
