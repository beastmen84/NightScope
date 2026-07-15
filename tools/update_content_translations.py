from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import OrderedDict
from functools import cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astro_viewer.app.services.localization import content_key  # noqa: E402
from tools.translation_provider import GoogleTranslator  # noqa: E402


DATA_DIR = PROJECT_ROOT / "astro_viewer" / "data"
TRANSLATIONS_DIR = PROJECT_ROOT / "astro_viewer" / "translations"
OBJECT_FIELDS = ("short_description", "observing_notes", "best_seen")
TRANSLATION_CHUNK_LIMIT = 4_000
SEPARATOR = "\n[NIGHTSCOPE_SPLIT_0001]\n"

_ENGLISH_CONTENT_OVERRIDES = {
    ("objects", "messier-M16", "observing_notes"): (
        "For M16 (Eagle Nebula), integrated magnitude 6.4, alternate between "
        "direct and averted vision while keeping the same exit pupil so the "
        "comparison remains reliable."
    ),
    ("objects", "messier-M26", "observing_notes"): (
        "M26 is about 14′ wide and has integrated magnitude 8.0; examine the "
        "cluster as a whole before evaluating its closest stellar pairs."
    ),
    ("objects", "messier-M56", "short_description"): (
        "M56 is a globular cluster in Lyra, between Lyra and Cygnus in a region "
        "already rich in targets. It is a subtle globular cluster that rewards "
        "patient observation rather than a quick glance."
    ),
    ("objects", "messier-M76", "observing_notes"): (
        "For M76 (Little Dumbbell Nebula), integrated magnitude 10.1, alternate "
        "between direct and averted vision while keeping the same exit pupil so "
        "the comparison remains reliable."
    ),
    ("objects", "caldwell-C1", "observing_notes"): (
        "Use a medium field under dark skies; increase magnification moderately "
        "to separate the many faint stars from the background."
    ),
    ("objects", "caldwell-C4", "observing_notes"): (
        "For C4 (NGC 7023 - Iris Nebula), integrated magnitude 6.8, alternate "
        "between direct and averted vision while keeping the same exit pupil so "
        "the comparison remains reliable."
    ),
    ("objects", "caldwell-C10", "observing_notes"): (
        "For C10 (NGC 663), integrated magnitude 7.1, start with a field wider "
        "than 16′; narrow it only if component separation improves."
    ),
    ("objects", "caldwell-C22", "observing_notes"): (
        "For C22 (NGC 7662 - Blue Snowball Nebula), integrated magnitude 9.2, "
        "alternate between direct and averted vision while keeping the same exit "
        "pupil so the comparison remains reliable."
    ),
    ("objects", "caldwell-C28", "observing_notes"): (
        "For C28 (NGC 752), integrated magnitude 5.7, start with a field wider "
        "than 50′; narrow it only if component separation improves."
    ),
    ("objects", "caldwell-C46", "observing_notes"): (
        "For C46 (NGC 2261 - Hubble's Variable Nebula), integrated magnitude "
        "10.0, alternate between direct and averted vision while keeping the "
        "same exit pupil so the comparison remains reliable."
    ),
    ("objects", "caldwell-C53", "observing_notes"): (
        "For C53 (NGC 3115 - Spindle Galaxy), magnitude 9.1 and dimensions "
        "8′ x 3′ must be considered together: surface contrast determines how "
        "much of the galaxy becomes visible."
    ),
    ("objects", "caldwell-C55", "observing_notes"): (
        "For C55 (NGC 7009 - Saturn Nebula), integrated magnitude 8.3, use its "
        "2.5′ x 1′ dimensions to keep the entire nebula in view before narrowing "
        "the field."
    ),
    ("objects", "caldwell-C58", "observing_notes"): (
        "For C58 (NGC 2360), integrated magnitude 7.2, start with a field wider "
        "than 13′; narrow it only if component separation improves."
    ),
    ("objects", "caldwell-C109", "observing_notes"): (
        "For C109 (NGC 3195), use its 0.6′ size to keep the entire nebula in view "
        "before narrowing the field."
    ),
    ("catalogue_objects", "caldwell-C13", "name"): "NGC 457 - Owl Cluster",
    ("catalogue_objects", "caldwell-C38", "name"): "NGC 4565 - Needle Galaxy",
    ("catalogue_objects", "caldwell-C53", "name"): "NGC 3115 - Spindle Galaxy",
    ("equipment_filters", "astronomik::uhc-e", "notes"): (
        "Moderate bandpass suitable for small apertures."
    ),
    ("equipment_filters", "baader::oiii super-g 9 nm", "notes"): (
        "Narrow OIII filter for medium to large apertures."
    ),
    ("equipment_filters", "baader::fringe killer", "notes"): (
        "Reduces chromatic aberration in achromatic refractors."
    ),
    ("equipment_reducers", "starizona::sct corrector iv::0.63", "notes"): (
        "Photographic focal reducer and corrector for classic SCTs."
    ),
    (
        "equipment_reducers",
        "starizona::night owl sct reducer-corrector::0.4",
        "connection",
    ): "2-inch body",
    (
        "equipment_reducers",
        "starizona::night owl sct reducer-corrector::0.4",
        "notes",
    ): "Fast photographic focal reducer for small sensors.",
    ("equipment_reducers", "william optics::flat 73r::0.8", "notes"): (
        "Dedicated focal reducer and field flattener."
    ),
    ("equipment_reducers", "william optics::ultra flat 91::0.79", "notes"): (
        "Dedicated focal reducer with a corrected field."
    ),
    ("equipment_reducers", "william optics::ultra flat 132::0.79", "notes"): (
        "Dedicated focal reducer with a corrected field."
    ),
    ("equipment_reducers", "william optics::ultra flat 156::0.79", "notes"): (
        "Dedicated focal reducer with a corrected field."
    ),
    (
        "equipment_reducers",
        "sky-watcher::0.85x reducer-corrector ed80::0.85",
        "connection",
    ): "M48 camera side",
    (
        "equipment_reducers",
        "sky-watcher::0.85x reducer-corrector ed100::0.85",
        "connection",
    ): "M48 camera side",
    (
        "equipment_reducers",
        "sky-watcher::0.85x reducer-corrector ed120::0.85",
        "connection",
    ): "M48 camera side",
}

_ENGLISH_TELESCOPE_LABELS = {
    "optical_type": {
        "refractor": "Refractor",
    },
    "mount_type": {
        "altazimuth": "Altazimuth",
        "Dobson": "Dobsonian",
        "Dobson tabletop": "Tabletop Dobsonian",
        "equatorial": "Equatorial",
        "equatorial CG-4": "CG-4 equatorial",
    },
}

_ENGLISH_OBJECT_TEXT_REPLACEMENTS = (
    ("multi-billion-dollar age", "multi-billion-year age"),
    ("planetary mixer", "planetary nebula"),
    ("discreet and not immediate", "subtle and not immediately obvious"),
    ("With a wide shot both can fit into the same frame.", "A wide field of view can include both galaxies."),
    ("before narrowing the frame.", "before narrowing the field."),
    ("it records central concentration", "record central concentration"),
    ("magnitude 6.3 is built in:", "with integrated magnitude 6.3:"),
    ("the dark sky counts more than the magnification", "dark-sky quality matters more than magnification"),
    ("the design of the group counts above all", "the overall pattern of the group matters most"),
    ("The figure of ", "The integrated magnitude of "),
    (" magnitudes concerns the entire object", " describes the entire object"),
    (
        "The first reading concerns the nucleus, orientation and shape of the halo",
        "Start by examining the nucleus, orientation, and shape of the halo",
    ),
    ("with more aperture and stable seeing", "with a larger aperture and steady seeing"),
    ("then move up with stable seeing", "then increase magnification when the seeing is steady"),
    ("the central star is sought without easy expectations", "the central star remains challenging"),
    ("increase moderately on M81", "increase magnification moderately on M81"),
    ("The rod and arms", "The bar and arms"),
    ("acquired in a fusion", "acquired through a merger"),
    ("trace of that ancient fusion", "trace of that ancient merger"),
    ("rejuvenated by fusions or transfers", "rejuvenated by mergers or transfers"),
    ("it initially preserves a field wider than", "start with a field wider than"),
    ("initially retains a field wider than", "start with a field wider than"),
    ("it initially retains a wider field of", "start with a field wider than"),
)


def source_language(section: str, item_key: str, field: str) -> str:
    """Returns the language actually used by each seed field.

    The bundled CSV files predate structured localization and legitimately mix
    Italian and English. Treating an entire section as one language caused
    source text to leak into the opposite locale and, on refresh, translated
    already translated content.
    """

    if section == "objects":
        return "it"
    if section == "catalogue_objects":
        return "it" if item_key.startswith("caldwell-") else "en"
    if section == "equipment_telescopes":
        return "en" if field == "notes" else "it"
    if section in {"equipment_eyepieces", "equipment_barlows"}:
        return "en"
    if section in {"equipment_filters", "equipment_reducers"}:
        return "it"
    raise KeyError(f"Unknown content section: {section}")


def _read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


@cache
def _caldwell_english_descriptions() -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for row in _read_csv("catalogue_objects_seed.csv"):
        object_id = row["object_id"].strip()
        if not object_id.startswith("caldwell-"):
            continue
        prefix = row["descrizione"].split(" - ", maxsplit=1)[0].strip()
        descriptions[object_id] = (
            f"{prefix} - {row['tipo'].strip()} in {row['costellazione'].strip()}."
        )
    return descriptions


def curate_content_translation(
    section: str,
    item_key: str,
    field: str,
    value: str,
    language_code: str,
) -> str:
    if language_code != "en":
        return value
    if section == "catalogue_objects" and field == "description":
        description = _caldwell_english_descriptions().get(item_key)
        if description:
            return description
    override = _ENGLISH_CONTENT_OVERRIDES.get((section, item_key, field))
    if override:
        return override
    if section == "equipment_telescopes":
        return _ENGLISH_TELESCOPE_LABELS.get(field, {}).get(value, value)
    if section == "objects":
        for source, replacement in _ENGLISH_OBJECT_TEXT_REPLACEMENTS:
            value = value.replace(source, replacement)
        value = re.sub(
            r"\b(On|In|For|With) ((?:M|C)\d+(?: \([^)]*\))?), of integrated magnitude",
            r"For \2, with integrated magnitude",
            value,
        )
        value = re.sub(
            r"\b(To evaluate (?:M|C)\d+), of integrated magnitude",
            r"\1, with integrated magnitude",
            value,
        )
        value = re.sub(
            r"The ([0-9.]+) magnitude figure concerns the entire object",
            r"The integrated magnitude of \1 describes the entire object",
            value,
        )
        value = re.sub(
            r"The ([0-9.]+) magnitude figure applies to the entire object",
            r"The integrated magnitude of \1 describes the entire object",
            value,
        )
        value = re.sub(
            r"the ([0-9.]+) integrated magnitude does not (?:alone|by itself) describe",
            r"an integrated magnitude of \1 does not by itself describe",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"total brightness corresponds to (?:the )?integrated magnitude ([0-9.]+)",
            r"total brightness corresponds to an integrated magnitude of \1",
            value,
            flags=re.IGNORECASE,
        )
        value = value.replace("Central at low magnification", "Center it at low magnification")
        value = value.replace("then move up", "then increase magnification")
        value = value.replace("and move up", "and increase magnification")
        value = value.replace(
            "searches for edge resolution first",
            "look for resolution at the edge first",
        )
        value = value.replace("for full extension", "to see its full extent")
        value = value.replace("in the frame", "in the field of view")
        value = value.replace("initially retains a wider field of", "start with a field wider than")
        value = value.replace("initially preserves a field wider than", "start with a field wider than")
        value = value.replace("identify him with certainty", "identify it with certainty")
        value = value.replace("make a bigger difference", "make a greater difference")
        value = value.replace("medium enlargements", "moderate magnification")
    if section in {"objects", "catalogue_objects"}:
        return re.sub(r"\b(NGC|IC)\s*(\d)", r"\1 \2", value)
    return value


def source_content() -> dict[str, dict[str, dict[str, str]]]:
    sections: dict[str, dict[str, dict[str, str]]] = OrderedDict()
    objects: dict[str, dict[str, str]] = OrderedDict()
    for row in _read_csv("object_descriptions_seed.csv"):
        object_id = row["object_id"].strip()
        if object_id in objects:
            raise ValueError(f"Duplicate object translation key: {object_id}")
        objects[object_id] = {
            field: row[field].strip()
            for field in OBJECT_FIELDS
            if row.get(field, "").strip()
        }
    for row in _read_csv("object_curiosities_seed.csv"):
        object_id = row["object_id"].strip()
        if "curiosity_text" in objects.get(object_id, {}):
            raise ValueError(f"Duplicate object curiosity key: {object_id}")
        objects.setdefault(object_id, {})["curiosity_text"] = row[
            "curiosity_text"
        ].strip()
    sections["objects"] = objects

    catalogue_objects: dict[str, dict[str, str]] = OrderedDict()
    for row in _read_csv("catalogue_objects_seed.csv"):
        object_id = row["object_id"].strip()
        if object_id in catalogue_objects:
            raise ValueError(f"Duplicate catalogue translation key: {object_id}")
        name = row["nome"].strip()
        catalogue_objects[object_id] = {
            "name": name,
            "description": row["descrizione"].strip(),
        }
    sections["catalogue_objects"] = catalogue_objects

    equipment_specs = (
        (
            "equipment_telescopes",
            "telescope_catalog_seed.csv",
            ("brand", "model"),
            ("optical_type", "mount_type", "notes"),
        ),
        (
            "equipment_eyepieces",
            "eyepiece_catalog_seed.csv",
            (
                "brand",
                "model",
                "eyepiece_type",
                "focal_length_mm",
                "min_focal_length_mm",
                "max_focal_length_mm",
            ),
            ("notes",),
        ),
        (
            "equipment_barlows",
            "barlow_catalog_seed.csv",
            ("brand", "model", "multiplier"),
            ("notes",),
        ),
        (
            "equipment_filters",
            "filter_catalog_seed.csv",
            ("brand", "model"),
            ("notes",),
        ),
        (
            "equipment_reducers",
            "reducer_catalog_seed.csv",
            ("brand", "model", "reduction_factor"),
            ("compatible_models", "connection", "notes"),
        ),
    )
    for section, filename, identity_fields, fields in equipment_specs:
        items: dict[str, dict[str, str]] = OrderedDict()
        for row in _read_csv(filename):
            key = content_key(*(row.get(field, "") for field in identity_fields))
            if key in items:
                raise ValueError(
                    f"Duplicate equipment translation key in {filename}: {key}"
                )
            items[key] = {
                field: row[field].strip()
                for field in fields
                if row.get(field, "").strip()
            }
        sections[section] = items
    return sections


def _chunks(values: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    current_size = 0
    for value in values:
        added_size = len(value) + (len(SEPARATOR) if current else 0)
        if current and current_size + added_size > TRANSLATION_CHUNK_LIMIT:
            chunks.append(current)
            current = []
            current_size = 0
        current.append(value)
        current_size += len(value) + (len(SEPARATOR) if len(current) > 1 else 0)
    if current:
        chunks.append(current)
    return chunks


def _translate_chunk(translator: GoogleTranslator, values: list[str]) -> list[str]:
    source = SEPARATOR.join(values)
    for attempt in range(4):
        try:
            translated = translator.translate(source)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
            continue
        parts = [part.strip() for part in translated.split("[NIGHTSCOPE_SPLIT_0001]")]
        if len(parts) == len(values) and all(parts):
            return parts
        if len(values) == 1 and translated.strip():
            return [translated.strip()]
        if attempt == 3:
            raise RuntimeError("Translation provider changed a NightScope batch separator.")
        time.sleep(1.5 * (attempt + 1))
    raise AssertionError("unreachable")


def translate_values(
    values: list[str],
    language_code: str,
    *,
    source_language: str,
) -> dict[str, str]:
    unique_values = list(dict.fromkeys(value for value in values if value))
    translator = GoogleTranslator(source=source_language, target=language_code)
    translations: dict[str, str] = {}
    chunks = _chunks(unique_values)
    for index, chunk in enumerate(chunks, start=1):
        translated = _translate_chunk(translator, chunk)
        translations.update(zip(chunk, translated, strict=True))
        print(
            f"{source_language}->{language_code}: "
            f"translated batch {index}/{len(chunks)}"
        )
        time.sleep(0.15)
    return translations


def update_pack(language_code: str, *, refresh: bool) -> None:
    metadata_path = TRANSLATIONS_DIR / f"{language_code}.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    if payload.get("language", {}).get("code") != language_code:
        raise ValueError(f"Language metadata mismatch: {metadata_path}")
    translation_code = str(
        payload.get("language", {}).get("translation_code") or language_code
    )

    sources = source_content()
    current_content = payload.get("content")
    if not isinstance(current_content, dict):
        current_content = {}

    required_by_source: dict[str, list[str]] = OrderedDict()
    for section, items in sources.items():
        for item_key, fields in items.items():
            existing = current_content.get(section, {}).get(item_key, {})
            for field, source in fields.items():
                field_source_language = source_language(section, item_key, field)
                if translation_code == field_source_language:
                    continue
                if refresh or not str(existing.get(field, "")).strip():
                    required_by_source.setdefault(field_source_language, []).append(source)
    translated: dict[str, str] = {}
    for source_code, required in required_by_source.items():
        translated.update(
            translate_values(
                required,
                translation_code,
                source_language=source_code,
            )
        )

    content: dict[str, dict[str, dict[str, str]]] = OrderedDict()
    for section, items in sources.items():
        translated_items: dict[str, dict[str, str]] = OrderedDict()
        for item_key, fields in items.items():
            existing = current_content.get(section, {}).get(item_key, {})
            translated_fields: dict[str, str] = OrderedDict()
            for field, source in fields.items():
                if translation_code == source_language(section, item_key, field):
                    continue
                previous = str(existing.get(field, "")).strip()
                value = translated.get(source) if refresh or not previous else previous
                translated_fields[field] = curate_content_translation(
                    section,
                    item_key,
                    field,
                    str(value or source).strip(),
                    translation_code,
                )
            if translated_fields:
                translated_items[item_key] = translated_fields
        if translated_items:
            content[section] = translated_items
    payload["content"] = content
    metadata_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate NightScope structured language-pack content from seed CSV files."
    )
    parser.add_argument(
        "languages",
        nargs="*",
        help="Language-pack codes to update; defaults to every discovered JSON pack.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Replace existing generated content instead of filling only missing fields.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    languages = args.languages or sorted(path.stem for path in TRANSLATIONS_DIR.glob("*.json"))
    for language_code in languages:
        update_pack(language_code, refresh=args.refresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
