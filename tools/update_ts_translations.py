from __future__ import annotations

import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ElementTree
from collections import OrderedDict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.translation_provider import GoogleTranslator  # noqa: E402


TRANSLATIONS_DIR = PROJECT_ROOT / "astro_viewer" / "translations"
TRANSLATION_CHUNK_LIMIT = 3_500
SEPARATOR = "\n[NIGHTSCOPE_TS_SPLIT_0001]\n"
PLACEHOLDER_PATTERN = re.compile(
    r"%L?\d+|%n|\{[A-Za-z_][A-Za-z0-9_]*(?:![rsa])?(?::[^{}]+)?\}"
)
MASK_PATTERN = re.compile(r"\[NIGHTSCOPE_PH_(\d{4})\]", re.IGNORECASE)


def _language_packs() -> dict[str, dict]:
    packs: dict[str, dict] = {}
    for path in sorted(TRANSLATIONS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        language = payload.get("language", {})
        code = str(language.get("code") or "").strip().lower()
        if payload.get("schema_version") != 1 or code != path.stem:
            raise ValueError(f"Invalid language pack: {path}")
        packs[code] = payload
    source = [
        code
        for code, payload in packs.items()
        if bool(payload.get("language", {}).get("source"))
    ]
    if len(source) != 1:
        raise ValueError("Exactly one source language pack is required.")
    return packs


def _translation_code(payload: dict) -> str:
    language = payload["language"]
    return str(language.get("translation_code") or language["code"])


def _mask_placeholders(value: str) -> tuple[str, tuple[str, ...]]:
    placeholders: list[str] = []

    def replace(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"[NIGHTSCOPE_PH_{len(placeholders) - 1:04d}]"

    return PLACEHOLDER_PATTERN.sub(replace, value), tuple(placeholders)


def _restore_placeholders(value: str, placeholders: tuple[str, ...]) -> str:
    seen: list[int] = []

    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index >= len(placeholders):
            raise ValueError("Translation provider introduced an unknown placeholder.")
        seen.append(index)
        return placeholders[index]

    restored = MASK_PATTERN.sub(replace, value)
    if sorted(seen) != list(range(len(placeholders))):
        raise ValueError("Translation provider removed or duplicated a placeholder.")
    return restored


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
        current_size += added_size
    if current:
        chunks.append(current)
    return chunks


def _translate_chunk(translator: GoogleTranslator, values: list[str]) -> list[str]:
    joined = SEPARATOR.join(values)
    for attempt in range(4):
        try:
            translated = translator.translate(joined)
            parts = [
                part.strip()
                for part in translated.split("[NIGHTSCOPE_TS_SPLIT_0001]")
            ]
            if len(parts) == len(values) and all(parts):
                return parts
            if len(values) == 1 and translated.strip():
                return [translated.strip()]
        except Exception:
            if attempt == 3:
                raise
        if attempt == 3:
            raise RuntimeError(
                "Translation provider changed a NightScope TS batch separator."
            )
        time.sleep(1.5 * (attempt + 1))
    raise AssertionError("unreachable")


def translate_values(
    values: list[str],
    *,
    source_language: str,
    target_language: str,
) -> dict[str, str]:
    unique = list(OrderedDict.fromkeys(value for value in values if value))
    masked_values: list[str] = []
    placeholders_by_value: dict[str, tuple[str, ...]] = {}
    for value in unique:
        masked, placeholders = _mask_placeholders(value)
        masked_values.append(masked)
        placeholders_by_value[value] = placeholders

    translator = GoogleTranslator(source=source_language, target=target_language)
    translated_masked: list[str] = []
    chunks = _chunks(masked_values)
    for index, chunk in enumerate(chunks, start=1):
        translated_masked.extend(_translate_chunk(translator, chunk))
        print(
            f"{source_language}->{target_language}: "
            f"translated TS batch {index}/{len(chunks)}"
        )
        time.sleep(0.15)

    translations: dict[str, str] = {}
    for source, translated in zip(unique, translated_masked, strict=True):
        restored = _restore_placeholders(
            translated,
            placeholders_by_value[source],
        )
        if sorted(PLACEHOLDER_PATTERN.findall(restored)) != sorted(
            PLACEHOLDER_PATTERN.findall(source)
        ):
            raise ValueError(f"Placeholder mismatch after translation: {source}")
        translations[source] = restored
    return translations


def _write_catalog(path: Path, root: ElementTree.Element) -> None:
    ElementTree.indent(root, space="  ")
    body = ElementTree.tostring(root, encoding="unicode", short_empty_elements=True)
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS []>\n'
        + body
        + "\n",
        encoding="utf-8",
    )


def update_catalog(
    language_code: str,
    payload: dict,
    *,
    source_language: str,
    refresh: bool,
) -> None:
    path = TRANSLATIONS_DIR / f"{language_code}.ts"
    root = ElementTree.parse(path).getroot()
    messages = root.findall(".//message")
    pending: list[ElementTree.Element] = []
    for message in messages:
        translation = message.find("translation")
        if translation is None:
            translation = ElementTree.SubElement(message, "translation")
        if translation.get("type") in {"obsolete", "vanished"}:
            continue
        incomplete = translation.get("type") == "unfinished" or not (
            translation.text or ""
        ).strip()
        if refresh or incomplete:
            pending.append(message)

    sources = [message.findtext("source", default="") for message in pending]
    target_language = _translation_code(payload)
    translations = (
        {source: source for source in sources}
        if target_language == source_language
        else translate_values(
            sources,
            source_language=source_language,
            target_language=target_language,
        )
    )
    for message in pending:
        source = message.findtext("source", default="")
        translation = message.find("translation")
        if translation is None:
            raise AssertionError("translation node disappeared")
        translation.text = translations[source]
        translation.attrib.pop("type", None)
    _write_catalog(path, root)
    print(f"{language_code}: updated {len(pending)} TS messages")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate NightScope Qt TS catalogs from discovered language packs."
    )
    parser.add_argument(
        "languages",
        nargs="*",
        help="Target language-pack codes; defaults to every non-source pack.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Replace completed translations instead of filling only missing messages.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packs = _language_packs()
    source_codes = [
        code
        for code, payload in packs.items()
        if bool(payload["language"].get("source"))
    ]
    source_code = source_codes[0]
    source_language = _translation_code(packs[source_code])
    languages = args.languages or [
        code for code in sorted(packs) if code != source_code
    ]
    unknown = sorted(set(languages) - set(packs))
    if unknown:
        raise ValueError(f"Unknown language packs: {', '.join(unknown)}")
    for language_code in languages:
        if language_code == source_code:
            continue
        update_catalog(
            language_code,
            packs[language_code],
            source_language=source_language,
            refresh=args.refresh,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
