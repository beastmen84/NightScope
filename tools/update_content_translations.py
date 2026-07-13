from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import OrderedDict
from pathlib import Path

from deep_translator import GoogleTranslator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astro_viewer.app.services.localization import content_key  # noqa: E402


DATA_DIR = PROJECT_ROOT / "astro_viewer" / "data"
TRANSLATIONS_DIR = PROJECT_ROOT / "astro_viewer" / "translations"
OBJECT_FIELDS = ("short_description", "observing_notes", "best_seen")
TRANSLATION_CHUNK_LIMIT = 4_000
SEPARATOR = "\n[NIGHTSCOPE_SPLIT_0001]\n"
SECTION_SOURCE_LANGUAGES = {
    "objects": "it",
    "catalogue_objects": "en",
    "equipment_telescopes": "en",
    "equipment_eyepieces": "en",
    "equipment_barlows": "en",
    "equipment_filters": "en",
    "equipment_reducers": "en",
}
def _read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


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
            ("connection", "notes"),
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
        source_language = SECTION_SOURCE_LANGUAGES[section]
        if translation_code == source_language:
            continue
        for item_key, fields in items.items():
            existing = current_content.get(section, {}).get(item_key, {})
            for field, source in fields.items():
                if refresh or not str(existing.get(field, "")).strip():
                    required_by_source.setdefault(source_language, []).append(source)
    translated: dict[str, str] = {}
    for source_language, required in required_by_source.items():
        translated.update(
            translate_values(
                required,
                translation_code,
                source_language=source_language,
            )
        )

    content: dict[str, dict[str, dict[str, str]]] = OrderedDict()
    for section, items in sources.items():
        if translation_code == SECTION_SOURCE_LANGUAGES[section]:
            continue
        translated_items: dict[str, dict[str, str]] = OrderedDict()
        for item_key, fields in items.items():
            existing = current_content.get(section, {}).get(item_key, {})
            translated_fields: dict[str, str] = OrderedDict()
            for field, source in fields.items():
                previous = str(existing.get(field, "")).strip()
                value = translated.get(source) if refresh or not previous else previous
                translated_fields[field] = str(value or source).strip()
            translated_items[item_key] = translated_fields
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
