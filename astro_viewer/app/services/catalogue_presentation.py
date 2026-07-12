from __future__ import annotations


_OBJECT_TYPE_LABELS = {
    "asterism": "Asterismo",
    "barred spiral galaxy": "Galassia spirale barrata",
    "diffuse nebula": "Nebulosa diffusa",
    "dark nebula": "Nebulosa oscura",
    "dwarf elliptical galaxy": "Galassia ellittica nana",
    "elliptical galaxy": "Galassia ellittica",
    "galaxy": "Galassia",
    "globular cluster": "Ammasso globulare",
    "h ii region nebula": "Nebulosa H II",
    "h ii region nebula (part of the orion nebula)": "Nebulosa H II di Orione",
    "h ii region nebula with cluster": "Nebulosa H II con ammasso",
    "irregular galaxy": "Galassia irregolare",
    "lenticular galaxy": "Galassia lenticolare",
    "milky way star cloud": "Nube stellare della Via Lattea",
    "nebula": "Nebulosa",
    "nebula with cluster": "Nebulosa con ammasso",
    "open cluster": "Ammasso aperto",
    "optical double": "Doppia ottica",
    "planetary nebula": "Nebulosa planetaria",
    "peculiar galaxy": "Galassia peculiare",
    "seyfert galaxy": "Galassia di Seyfert",
    "spiral galaxy": "Galassia spirale",
    "starburst galaxy": "Galassia starburst",
    "supernova remnant": "Resto di supernova",
}

_OBSERVATION_TYPE_LABELS = {
    "general": "Generale",
    "highmagnification": "Alto ingrandimento",
    "widefield": "Campo largo",
}


def catalogue_object_type_label(value: str) -> str:
    clean = value.strip()
    return _OBJECT_TYPE_LABELS.get(clean.casefold(), clean)


def catalogue_observation_type_label(value: str) -> str:
    clean = value.strip()
    return _OBSERVATION_TYPE_LABELS.get(clean.casefold(), clean)
