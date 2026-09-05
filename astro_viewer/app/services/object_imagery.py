"""Resolve category illustrations and explicit images without loading pixel data.

Catalogue type names are canonical source values, never translated UI labels.
Unknown types deliberately use the neutral illustration, not an assumed cluster.
Keep retirement detection conservative: only known distributed asset identities,
paths and licenses may be removed during a database upgrade.
"""

from __future__ import annotations

from collections.abc import Mapping


SOLAR_SYSTEM_IMAGE_IDS = frozenset(
    {"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"}
)
CATEGORY_IMAGE_KEYS = (
    "galaxy", "galaxy_system", "open_cluster", "globular_cluster", "nebula",
    "emission_nebula", "reflection_nebula", "dark_nebula", "planetary_nebula",
    "nebula_cluster", "supernova_remnant", "asterism", "star_cloud", "star",
    "double_star", "unclassified",
)
ILLUSTRATION_LICENSE = "NightScope AI-generated category illustration"
_TYPE_CATEGORIES = {
    "galaxy": "galaxy",
    "barred spiral galaxy": "galaxy",
    "dwarf elliptical galaxy": "galaxy",
    "elliptical galaxy": "galaxy",
    "irregular galaxy": "galaxy",
    "lenticular galaxy": "galaxy",
    "peculiar galaxy": "galaxy",
    "seyfert galaxy": "galaxy",
    "spiral galaxy": "galaxy",
    "starburst galaxy": "galaxy",
    "galaxy group": "galaxy_system",
    "galaxy pair": "galaxy_system",
    "galaxy triplet": "galaxy_system",
    "open cluster": "open_cluster",
    "globular cluster": "globular_cluster",
    "nebula": "nebula",
    "diffuse nebula": "nebula",
    "emission nebula": "emission_nebula",
    "h ii region nebula": "emission_nebula",
    "h ii region nebula (part of the orion nebula)": "emission_nebula",
    "reflection nebula": "reflection_nebula",
    "dark nebula": "dark_nebula",
    "planetary nebula": "planetary_nebula",
    "nebula with cluster": "nebula_cluster",
    "h ii region nebula with cluster": "nebula_cluster",
    "supernova remnant": "supernova_remnant",
    "asterism": "asterism",
    "milky way star cloud": "star_cloud",
    "star": "star",
    "optical double": "double_star",
    "unclassified object": "unclassified",
    # Canonical Italian values retained by the deterministic mock catalogue.
    "galassia": "galaxy",
    "ammasso globulare": "globular_cluster",
    "nebulosa planetaria": "planetary_nebula",
}
_LEGACY_GENERATED_LICENSES = frozenset(
    {"NightScope local generated asset", "NightScope local generated placeholder"}
)
_RETIRED_SURVEY_LICENSES = frozenset(
    {
        "2MASS public survey data; CDS/P/2MASS/color HiPS ODbL-1.0",
        "Pan-STARRS1 public data; CDS Pan-STARRS DR1 HiPS ODbL-1.0",
        "SkyMapper DR4 public data; CDS SkyMapper DR4 HiPS ODbL-1.0",
    }
)
# Exact identities shipped before 1.46.11, not a wildcard on catalogue prefixes.
_RETIRED_PHOTO_IDS = frozenset(
    [f"messier-M{number}" for number in range(1, 111)]
    + [f"caldwell-C{number}" for number in range(1, 110)]
)
_RETIRED_DEFAULT_PATHS = {
    "messier-default-galaxy": "resources/images/m31.svg",
    "messier-default-nebula": "resources/images/m57.svg",
    "messier-default-cluster": "resources/images/m13.svg",
}


def image_category(object_type: str) -> str:
    """Map an exact catalogue type to a shared, explicitly schematic illustration."""
    return _TYPE_CATEGORIES.get(" ".join(object_type.split()).casefold(), "unclassified")


def category_image(category: str) -> dict:
    """Return immutable-by-convention metadata, not an object-specific observation."""
    if category not in CATEGORY_IMAGE_KEYS:
        category = "unclassified"
    path = f"resources/images/categories/{category}.jpg"
    return {
        "image_path": path,
        "thumbnail_path": path,
        "attribution": "NightScope",
        "source_url": "",
        "license": ILLUSTRATION_LICENSE,
        "verified": False,
        "kind": "illustration",
        "category": category,
    }


def retired_builtin_image(row: Mapping) -> bool:
    """Recognize retired distributed imagery without treating custom rows as seeds."""
    object_id = str(row.get("object_id") or "")
    path = str(row.get("image_path") or "")
    license_label = str(row.get("license") or "")
    legacy_generated = license_label in _LEGACY_GENERATED_LICENSES
    if object_id in _RETIRED_DEFAULT_PATHS:
        return legacy_generated and path == _RETIRED_DEFAULT_PATHS[object_id]
    if object_id not in _RETIRED_PHOTO_IDS:
        return False
    if legacy_generated:
        return path in _RETIRED_DEFAULT_PATHS.values() or path == (
            f"resources/images/catalogue/{object_id}.jpg"
        )
    return (
        license_label in _RETIRED_SURVEY_LICENSES
        and path == f"resources/images/catalogue/{object_id}.jpg"
    )


def resolve_object_image(
    object_id: str,
    object_type: str,
    object_images: Mapping[str, Mapping],
) -> dict:
    """Prefer explicit non-retired imagery; otherwise use the correct default.

    Solar System originals remain specific to each body. All deep-sky catalogues
    share the category policy, independent of whether editorial content is ready.
    Legacy custom rows remain intact; personal-image storage is a separate layer.
    """
    candidate = object_images.get(object_id)
    if candidate and candidate.get("image_path") and not retired_builtin_image(
        {**candidate, "object_id": object_id}
    ):
        return {
            **candidate,
            "kind": "solar_system" if (
                object_id in SOLAR_SYSTEM_IMAGE_IDS
                and candidate["image_path"] == f"resources/images/solar_system/{object_id}.jpg"
            ) else "personal",
            "category": "",
        }
    if object_id in SOLAR_SYSTEM_IMAGE_IDS:
        path = f"resources/images/solar_system/{object_id}.jpg"
        return {
            "image_path": path, "thumbnail_path": path, "attribution": "",
            "source_url": "", "license": "", "verified": False,
            "kind": "solar_system", "category": "",
        }
    return category_image(image_category(object_type))
