"""Audit canonical catalogue prose, translations, provenance, and batch reviews."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]

DESCRIPTION_FIELDS = (
    "short_description",
    "observing_notes",
    "best_seen",
    "difficulty_naked_eye",
    "difficulty_binocular",
    "difficulty_small_scope",
    "difficulty_medium_scope",
    "difficulty_large_scope",
)
TRANSLATED_FIELDS = (
    "short_description",
    "observing_notes",
    "best_seen",
    "curiosity_text",
)
NARRATIVE_FIELDS = (
    "short_description",
    "observing_notes",
    "curiosity_text",
)
REVIEW_KEYS = ("facts", "it", "en", "es")
REVIEW_STATES = frozenset({"pending", "accepted"})
PLACEHOLDERS = frozenset(
    {
        "work in progress",
        "lavori in corso",
        "trabajo en curso",
        "trabajo en progreso",
    }
)
VERSION_PATTERN = re.compile(r"1\.46\.(?P<patch>\d+)")
TOKEN_PATTERN = re.compile(r"[^\W\d_]+", re.UNICODE)
CATALOGUE_ID_PATTERN = re.compile(r"\b(?:ngc|ic|m|c)\s*\d+[a-z]?\b", re.IGNORECASE)
PARENTHETICAL_DETAIL_PATTERN = re.compile(r"\([^)]*\)")
NEAR_DUPLICATE_THRESHOLD = 0.88
SOLAR_SYSTEM_IDS = frozenset(
    {
        "sun",
        "moon",
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
    }
)


@dataclass(frozen=True)
class EditorialAuditReport:
    """Describe deterministic repository coverage and every acceptance failure."""

    catalogue_objects: int
    ngc_only_objects: int
    baseline_objects: int
    completed_objects: int
    completed_ngc_objects: int
    remaining_ngc_objects: int
    accepted_batches: int
    draft_batches: int
    baseline_description_template_families: int
    baseline_description_template_objects: int
    baseline_observing_template_families: int
    baseline_observing_template_objects: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class _ManifestRecord:
    path: Path
    version: str
    status: str
    object_ids: tuple[str, ...]
    waivers: frozenset[tuple[str, str, str, str]]


def _read_csv(
    path: Path,
    required_fields: tuple[str, ...],
    errors: list[str],
) -> list[dict[str, str]]:
    if not path.is_file():
        errors.append(f"missing CSV: {path}")
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            fields = set(reader.fieldnames or ())
            missing = sorted(set(required_fields) - fields)
            if missing:
                errors.append(f"{path.name}: missing columns {', '.join(missing)}")
                return []
            return [dict(row) for row in reader]
    except (OSError, UnicodeError, csv.Error) as error:
        errors.append(f"cannot read {path}: {error}")
        return []


def _index_rows(
    rows: list[dict[str, str]],
    label: str,
    errors: list[str],
) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for number, row in enumerate(rows, start=2):
        object_id = str(row.get("object_id") or "").strip()
        if not object_id:
            errors.append(f"{label}:{number}: empty object_id")
            continue
        if object_id in indexed:
            errors.append(f"{label}: duplicate object_id {object_id}")
            continue
        indexed[object_id] = row
    return indexed


def _read_json(path: Path, label: str, errors: list[str]) -> dict:
    if not path.is_file():
        errors.append(f"missing JSON: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"cannot read {label}: {error}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label}: root must be an object")
        return {}
    return payload


def _pack_objects(path: Path, language: str, errors: list[str]) -> dict[str, dict]:
    payload = _read_json(path, f"{language} language pack", errors)
    content = payload.get("content")
    objects = content.get("objects") if isinstance(content, dict) else None
    if not isinstance(objects, dict):
        errors.append(f"{language} language pack: content.objects must be an object")
        return {}
    return {
        str(object_id): fields
        for object_id, fields in objects.items()
        if isinstance(fields, dict)
    }


def _is_https_url(value: str | None) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def _is_iso_date(value: str | None) -> bool:
    if value is None:
        return False
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def _normalized(value: str | None) -> str:
    return " ".join(str(value or "").split()).casefold()


def _is_placeholder(value: str | None) -> bool:
    return _normalized(value) in PLACEHOLDERS


def _baseline_digest(object_ids: set[str]) -> str:
    joined = "\n".join(sorted(object_ids)).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()


def _duplicate_text_errors(
    language: str,
    field: str,
    values: dict[str, str],
) -> list[str]:
    by_text: dict[str, list[str]] = defaultdict(list)
    for object_id, value in values.items():
        normalized = _normalized(value)
        if normalized:
            by_text[normalized].append(object_id)
    return [
        f"{language} {field}: duplicate text for {', '.join(sorted(object_ids))}"
        for object_ids in by_text.values()
        if len(object_ids) > 1
    ]


def _manifest_paths(root: Path, batch_path: Path | None) -> tuple[Path, ...]:
    paths = set((root / "astro_viewer/data/editorial_batches").glob("batch_*.json"))
    if batch_path is not None:
        selected = batch_path if batch_path.is_absolute() else root / batch_path
        paths.add(selected)
    return tuple(sorted(path.resolve() for path in paths))


def _validate_manifest(
    path: Path,
    payload: dict,
    *,
    catalogue: dict[str, dict[str, str]],
    designations: dict[str, tuple[str, ...]],
    descriptions: dict[str, dict[str, str]],
    curiosities: dict[str, dict[str, str]],
    translations: dict[str, dict[str, dict]],
    errors: list[str],
) -> _ManifestRecord:
    label = path.name
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        errors.append(f"{label}: schema_version must be 1")

    version = str(payload.get("source_version") or "").strip()
    version_match = VERSION_PATTERN.fullmatch(version)
    if version_match is None or int(version_match.group("patch")) < 1:
        errors.append(f"{label}: source_version must be 1.46.1 or a later 1.46.x patch")
    expected_name = f"batch_{version.replace('.', '_')}.json" if version else ""
    if expected_name and path.name != expected_name:
        errors.append(f"{label}: filename must be {expected_name}")

    status = str(payload.get("status") or "").strip()
    if status not in {"draft", "accepted"}:
        errors.append(f"{label}: status must be draft or accepted")
    if not str(payload.get("selection_basis") or "").strip():
        errors.append(f"{label}: selection_basis is required")
    if not _is_iso_date(payload.get("created_on")):
        errors.append(f"{label}: created_on must be an ISO date")
    if status == "accepted" and not _is_iso_date(payload.get("reviewed_on")):
        errors.append(f"{label}: accepted batch needs an ISO reviewed_on date")

    raw_objects = payload.get("objects")
    if not isinstance(raw_objects, list) or not raw_objects:
        errors.append(f"{label}: objects must contain between 1 and 100 entries")
        raw_objects = []
    elif len(raw_objects) > 100:
        errors.append(f"{label}: objects exceeds the 100-object ceiling")

    object_ids: list[str] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_objects, start=1):
        item_label = f"{label}:objects[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label}: entry must be an object")
            continue
        object_id = str(item.get("object_id") or "").strip()
        if not object_id:
            errors.append(f"{item_label}: object_id is required")
            continue
        if object_id in seen_ids:
            errors.append(f"{label}: duplicate manifest object_id {object_id}")
            continue
        seen_ids.add(object_id)
        object_ids.append(object_id)

        if object_id not in catalogue:
            errors.append(f"{item_label}: unknown physical object_id {object_id}")
        if not object_id.startswith("ngc-"):
            errors.append(f"{item_label}: editorial batches are restricted to NGC-only IDs")

        raw_designations = item.get("designations")
        manifest_designations = (
            tuple(sorted(str(value).strip() for value in raw_designations if str(value).strip()))
            if isinstance(raw_designations, list)
            else ()
        )
        expected_designations = designations.get(object_id, ())
        if manifest_designations != expected_designations:
            errors.append(
                f"{item_label}: designations must equal "
                f"{list(expected_designations)!r}"
            )

        reviews = item.get("reviews")
        reviews = reviews if isinstance(reviews, dict) else {}
        for review_key in REVIEW_KEYS:
            review_state = str(reviews.get(review_key) or "").strip()
            if review_state not in REVIEW_STATES:
                errors.append(
                    f"{item_label}: review {review_key} must be pending or accepted"
                )
            if status == "accepted" and review_state != "accepted":
                errors.append(f"{item_label}: review {review_key} must be accepted")

        raw_sources = item.get("sources")
        if not isinstance(raw_sources, list) or not raw_sources:
            errors.append(f"{item_label}: at least one evidence source is required")
            raw_sources = []
        supported_claims: set[str] = set()
        source_pairs: set[tuple[str, str]] = set()
        for source_index, source in enumerate(raw_sources, start=1):
            source_label = f"{item_label}:sources[{source_index}]"
            if not isinstance(source, dict):
                errors.append(f"{source_label}: source must be an object")
                continue
            visible_label = str(source.get("label") or "").strip()
            url = str(source.get("url") or "").strip()
            if not visible_label:
                errors.append(f"{source_label}: label is required")
            if not _is_https_url(url):
                errors.append(f"{source_label}: url must be a direct HTTPS URL")
            if not _is_iso_date(source.get("accessed_on")):
                errors.append(f"{source_label}: accessed_on must be an ISO date")
            raw_claims = source.get("supports")
            claims = (
                {str(value).strip() for value in raw_claims if str(value).strip()}
                if isinstance(raw_claims, list)
                else set()
            )
            unknown_claims = sorted(claims - set(TRANSLATED_FIELDS))
            if unknown_claims:
                errors.append(
                    f"{source_label}: unsupported claims {', '.join(unknown_claims)}"
                )
            supported_claims.update(claims)
            source_pairs.add((visible_label, url))

        if status == "accepted":
            missing_claims = sorted(set(TRANSLATED_FIELDS) - supported_claims)
            if missing_claims:
                errors.append(
                    f"{item_label}: sources do not cover {', '.join(missing_claims)}"
                )
            if object_id not in descriptions or object_id not in curiosities:
                errors.append(f"{item_label}: accepted object lacks complete Italian seeds")
            curiosity = curiosities.get(object_id) or {}
            curiosity_pair = (
                str(curiosity.get("source_label") or "").strip(),
                str(curiosity.get("source_url") or "").strip(),
            )
            if curiosity_pair not in source_pairs:
                errors.append(
                    f"{item_label}: curiosity seed source is absent from manifest evidence"
                )
            for language, localized in translations.items():
                fields = localized.get(object_id)
                if not isinstance(fields, dict) or any(
                    not str(fields.get(field) or "").strip()
                    for field in TRANSLATED_FIELDS
                ):
                    errors.append(
                        f"{item_label}: accepted object lacks complete {language} overlay"
                    )

    visual_review = payload.get("visual_review")
    visual_review = visual_review if isinstance(visual_review, dict) else {}
    samples = visual_review.get("samples")
    samples = samples if isinstance(samples, list) else []
    if status == "accepted":
        minimum_samples = min(5, len(object_ids))
        sampled_ids = {
            str(sample.get("object_id") or "").strip()
            for sample in samples
            if isinstance(sample, dict)
        }
        if len(sampled_ids) < minimum_samples:
            errors.append(
                f"{label}: accepted visual review needs at least {minimum_samples} "
                "distinct samples"
            )
        for sample_index, sample in enumerate(samples, start=1):
            sample_label = f"{label}:visual_review.samples[{sample_index}]"
            if not isinstance(sample, dict):
                errors.append(f"{sample_label}: sample must be an object")
                continue
            sample_id = str(sample.get("object_id") or "").strip()
            if sample_id not in seen_ids:
                errors.append(f"{sample_label}: object_id is outside this batch")
            if not str(sample.get("reason") or "").strip():
                errors.append(f"{sample_label}: reason is required")
            for mode in ("normal", "red_night_vision"):
                if str(sample.get(mode) or "").strip() != "accepted":
                    errors.append(f"{sample_label}: {mode} must be accepted")

    waivers: set[tuple[str, str, str, str]] = set()
    raw_waivers = payload.get("similarity_waivers", [])
    if not isinstance(raw_waivers, list):
        errors.append(f"{label}: similarity_waivers must be a list")
        raw_waivers = []
    for waiver_index, waiver in enumerate(raw_waivers, start=1):
        waiver_label = f"{label}:similarity_waivers[{waiver_index}]"
        if not isinstance(waiver, dict):
            errors.append(f"{waiver_label}: waiver must be an object")
            continue
        language = str(waiver.get("language") or "").strip()
        field = str(waiver.get("field") or "").strip()
        first = str(waiver.get("object_id") or "").strip()
        second = str(waiver.get("other_object_id") or "").strip()
        reason = str(waiver.get("reason") or "").strip()
        if language not in {"it", "en", "es"}:
            errors.append(f"{waiver_label}: language must be it, en, or es")
        if field not in NARRATIVE_FIELDS:
            errors.append(f"{waiver_label}: field is not similarity-screened")
        if not first or not second or first == second:
            errors.append(f"{waiver_label}: two distinct object IDs are required")
        if not reason:
            errors.append(f"{waiver_label}: reason is required")
        first_id, second_id = sorted((first, second))
        waivers.add((language, field, first_id, second_id))

    return _ManifestRecord(
        path=path,
        version=version,
        status=status,
        object_ids=tuple(object_ids),
        waivers=frozenset(waivers),
    )


def _similarity_text(value: str | None) -> tuple[str, frozenset[str]]:
    without_ids = CATALOGUE_ID_PATTERN.sub(" ", _normalized(value))
    normalized = " ".join(TOKEN_PATTERN.findall(without_ids))
    return normalized, frozenset(TOKEN_PATTERN.findall(normalized))


def _template_fingerprint(value: str | None) -> str:
    """Normalize identity and measurements to expose parameterized prose."""

    without_parenthetical_details = PARENTHETICAL_DETAIL_PATTERN.sub(
        " ", _normalized(value)
    )
    without_ids = CATALOGUE_ID_PATTERN.sub(" ", without_parenthetical_details)
    return " ".join(TOKEN_PATTERN.findall(without_ids))


def _template_groups(
    values: dict[str, str],
    *,
    minimum_tokens: int = 12,
) -> tuple[tuple[str, ...], ...]:
    """Cluster repeated or near-identical long-form legacy fingerprints."""

    prepared: dict[str, tuple[str, frozenset[str]]] = {}
    for object_id, value in values.items():
        fingerprint = _template_fingerprint(value)
        if len(fingerprint.split()) >= minimum_tokens:
            prepared[object_id] = (fingerprint, frozenset(fingerprint.split()))

    neighbours: dict[str, set[str]] = defaultdict(set)
    object_ids = sorted(prepared)
    for index, object_id in enumerate(object_ids):
        text, tokens = prepared[object_id]
        for other_id in object_ids[index + 1 :]:
            other_text, other_tokens = prepared[other_id]
            if min(len(text), len(other_text)) / max(len(text), len(other_text)) < 0.72:
                continue
            token_score = len(tokens & other_tokens) / len(tokens | other_tokens)
            if token_score < 0.68:
                continue
            score = SequenceMatcher(None, text, other_text, autojunk=False).ratio()
            if score < NEAR_DUPLICATE_THRESHOLD:
                continue
            neighbours[object_id].add(other_id)
            neighbours[other_id].add(object_id)

    groups: list[tuple[str, ...]] = []
    visited: set[str] = set()
    for object_id in sorted(neighbours):
        if object_id in visited:
            continue
        stack = [object_id]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(neighbours[current] - component)
        visited.update(component)
        groups.append(tuple(sorted(component)))
    return tuple(groups)


def _near_duplicate_errors(
    selected_ids: set[str],
    completed_ids: set[str],
    descriptions: dict[str, dict[str, str]],
    curiosities: dict[str, dict[str, str]],
    translations: dict[str, dict[str, dict]],
    waivers: frozenset[tuple[str, str, str, str]],
) -> list[str]:
    language_content: dict[str, dict[str, dict[str, str]]] = {"it": {}}
    for object_id in completed_ids:
        language_content["it"][object_id] = {
            **descriptions[object_id],
            "curiosity_text": curiosities[object_id]["curiosity_text"],
        }
    language_content.update(translations)

    failures: list[str] = []
    for language, content in language_content.items():
        for field in NARRATIVE_FIELDS:
            prepared = {
                object_id: _similarity_text(fields.get(field, ""))
                for object_id, fields in content.items()
                if object_id in completed_ids
            }
            compared: set[tuple[str, str]] = set()
            for object_id in sorted(selected_ids & prepared.keys()):
                text, tokens = prepared[object_id]
                if not text or not tokens:
                    continue
                for other_id, (other_text, other_tokens) in prepared.items():
                    if object_id == other_id or not other_text or not other_tokens:
                        continue
                    first_id, second_id = sorted((object_id, other_id))
                    pair = (first_id, second_id)
                    if pair in compared:
                        continue
                    compared.add(pair)
                    if min(len(text), len(other_text)) / max(len(text), len(other_text)) < 0.72:
                        continue
                    token_score = len(tokens & other_tokens) / len(tokens | other_tokens)
                    if token_score < 0.68:
                        continue
                    score = SequenceMatcher(None, text, other_text, autojunk=False).ratio()
                    if score < NEAR_DUPLICATE_THRESHOLD:
                        continue
                    waiver = (language, field, pair[0], pair[1])
                    if waiver in waivers:
                        continue
                    failures.append(
                        f"{language} {field}: near-duplicate {pair[0]} / {pair[1]} "
                        f"({score:.3f}); rewrite or document a similarity waiver"
                    )
    return failures


def audit_catalogue_editorial(
    root: Path = ROOT,
    *,
    batch_path: Path | None = None,
) -> EditorialAuditReport:
    """Return a network-free audit of canonical content and review evidence."""

    root = root.resolve()
    data_dir = root / "astro_viewer" / "data"
    translation_dir = root / "astro_viewer" / "translations"
    errors: list[str] = []
    warnings: list[str] = []

    catalogue = _index_rows(
        _read_csv(
            data_dir / "catalogue_objects_seed.csv",
            ("object_id", "descrizione"),
            errors,
        ),
        "catalogue_objects_seed.csv",
        errors,
    )
    description_rows = _read_csv(
        data_dir / "object_descriptions_seed.csv",
        ("object_id", *DESCRIPTION_FIELDS),
        errors,
    )
    descriptions = _index_rows(
        description_rows,
        "object_descriptions_seed.csv",
        errors,
    )
    curiosity_rows = _read_csv(
        data_dir / "object_curiosities_seed.csv",
        ("object_id", "curiosity_text", "source_label", "source_url", "verified"),
        errors,
    )
    curiosities = _index_rows(
        curiosity_rows,
        "object_curiosities_seed.csv",
        errors,
    )
    designation_rows = _read_csv(
        data_dir / "catalogue_designations_seed.csv",
        ("object_id", "designation"),
        errors,
    )
    designation_lists: dict[str, list[str]] = defaultdict(list)
    for row in designation_rows:
        object_id = str(row.get("object_id") or "").strip()
        designation = str(row.get("designation") or "").strip()
        if object_id and designation:
            designation_lists[object_id].append(designation)
    designations = {
        object_id: tuple(sorted(set(values)))
        for object_id, values in designation_lists.items()
    }

    description_ids = set(descriptions)
    curiosity_ids = set(curiosities)
    if description_ids != curiosity_ids:
        for object_id in sorted(description_ids - curiosity_ids):
            errors.append(f"{object_id}: description exists without curiosity")
        for object_id in sorted(curiosity_ids - description_ids):
            errors.append(f"{object_id}: curiosity exists without description")
    completed_ids = description_ids & curiosity_ids
    unknown_editorial_ids = completed_ids - set(catalogue) - SOLAR_SYSTEM_IDS
    if unknown_editorial_ids:
        errors.append(
            "editorial IDs missing from physical catalogue: "
            + ", ".join(sorted(unknown_editorial_ids))
        )

    translations = {
        language: _pack_objects(
            translation_dir / f"{language}.json",
            language,
            errors,
        )
        for language in ("en", "es")
    }

    for object_id in sorted(completed_ids):
        description = descriptions[object_id]
        for field in DESCRIPTION_FIELDS:
            value = str(description.get(field) or "").strip()
            if not value:
                errors.append(f"{object_id}: empty Italian {field}")
            elif _is_placeholder(value):
                errors.append(f"{object_id}: placeholder in Italian {field}")
        curiosity = curiosities[object_id]
        curiosity_text = str(curiosity.get("curiosity_text") or "").strip()
        if not curiosity_text or _is_placeholder(curiosity_text):
            errors.append(f"{object_id}: missing Italian curiosity_text")
        if not str(curiosity.get("source_label") or "").strip():
            errors.append(f"{object_id}: missing curiosity source_label")
        if not _is_https_url(curiosity.get("source_url")):
            errors.append(f"{object_id}: curiosity source_url must be HTTPS")
        if str(curiosity.get("verified") or "").strip() != "1":
            errors.append(f"{object_id}: curiosity verified must equal 1")

        for language, localized in translations.items():
            fields = localized.get(object_id)
            if not isinstance(fields, dict):
                errors.append(f"{object_id}: missing {language} object overlay")
                continue
            for field in TRANSLATED_FIELDS:
                value = str(fields.get(field) or "").strip()
                if not value:
                    errors.append(f"{object_id}: empty {language} {field}")
                elif _is_placeholder(value):
                    errors.append(f"{object_id}: placeholder in {language} {field}")

    for language, localized in translations.items():
        orphaned = set(localized) - completed_ids
        if orphaned:
            errors.append(
                f"{language} object overlays without canonical content: "
                + ", ".join(sorted(orphaned))
            )

    italian_content = {
        object_id: {
            **descriptions[object_id],
            "curiosity_text": curiosities[object_id]["curiosity_text"],
        }
        for object_id in completed_ids
    }
    for language, content in {"it": italian_content, **translations}.items():
        for field in NARRATIVE_FIELDS:
            errors.extend(
                _duplicate_text_errors(
                    language,
                    field,
                    {
                        object_id: str(fields.get(field) or "")
                        for object_id, fields in content.items()
                        if object_id in completed_ids
                    },
                )
            )

    baseline_payload = _read_json(
        data_dir / "editorial_batches" / "baseline_1_45_22.json",
        "editorial baseline",
        errors,
    )
    baseline_ids = {object_id for object_id in completed_ids if not object_id.startswith("ngc-")}
    raw_baseline_count = baseline_payload.get("object_count")
    expected_baseline_count = (
        raw_baseline_count if isinstance(raw_baseline_count, int) else -1
    )
    expected_baseline_digest = str(baseline_payload.get("object_ids_sha256") or "")
    if baseline_payload.get("schema_version") != 1:
        errors.append("editorial baseline: schema_version must be 1")
    if baseline_payload.get("source_version") != "1.45.22":
        errors.append("editorial baseline: source_version must be 1.45.22")
    if expected_baseline_count != len(baseline_ids):
        errors.append(
            "editorial baseline count changed: "
            f"expected {expected_baseline_count}, found {len(baseline_ids)}"
        )
    actual_baseline_digest = _baseline_digest(baseline_ids)
    if expected_baseline_digest != actual_baseline_digest:
        errors.append(
            "editorial baseline identity changed: "
            f"expected {expected_baseline_digest}, found {actual_baseline_digest}"
        )

    baseline_description_templates = _template_groups(
        {
            object_id: descriptions[object_id]["short_description"]
            for object_id in baseline_ids
        }
    )
    baseline_observing_templates = _template_groups(
        {
            object_id: descriptions[object_id]["observing_notes"]
            for object_id in baseline_ids
        }
    )
    baseline_description_template_objects = len(
        {object_id for group in baseline_description_templates for object_id in group}
    )
    baseline_observing_template_objects = len(
        {object_id for group in baseline_observing_templates for object_id in group}
    )
    if baseline_description_templates or baseline_observing_templates:
        warnings.append(
            "historical editorial baseline contains repeated or near-identical prose debt: "
            f"{len(baseline_description_templates)} description families / "
            f"{baseline_description_template_objects} objects; "
            f"{len(baseline_observing_templates)} observing-note families / "
            f"{baseline_observing_template_objects} objects"
        )

    manifests: list[_ManifestRecord] = []
    selected_manifest: _ManifestRecord | None = None
    seen_versions: set[str] = set()
    seen_manifest_ids: set[str] = set()
    selected_resolved = None
    if batch_path is not None:
        selected_resolved = (
            batch_path if batch_path.is_absolute() else root / batch_path
        ).resolve()
    for path in _manifest_paths(root, batch_path):
        payload = _read_json(path, path.name, errors)
        manifest = _validate_manifest(
            path,
            payload,
            catalogue=catalogue,
            designations=designations,
            descriptions=descriptions,
            curiosities=curiosities,
            translations=translations,
            errors=errors,
        )
        manifests.append(manifest)
        if path == selected_resolved:
            selected_manifest = manifest
        if manifest.version in seen_versions:
            errors.append(f"duplicate editorial batch version {manifest.version}")
        seen_versions.add(manifest.version)
        for object_id in manifest.object_ids:
            if object_id in seen_manifest_ids:
                errors.append(f"{object_id}: appears in more than one batch manifest")
            seen_manifest_ids.add(object_id)

    accepted_manifests = [manifest for manifest in manifests if manifest.status == "accepted"]
    accepted_ids = {
        object_id
        for manifest in accepted_manifests
        for object_id in manifest.object_ids
    }
    managed_ids = completed_ids - baseline_ids
    for object_id in sorted(managed_ids - accepted_ids):
        errors.append(f"{object_id}: completed content lacks an accepted batch manifest")
    for object_id in sorted(accepted_ids - managed_ids):
        errors.append(f"{object_id}: accepted manifest lacks completed repository content")

    if selected_manifest is not None:
        errors.extend(
            _near_duplicate_errors(
                set(selected_manifest.object_ids),
                completed_ids,
                descriptions,
                curiosities,
                translations,
                selected_manifest.waivers,
            )
        )

    ngc_ids = {object_id for object_id in catalogue if object_id.startswith("ngc-")}
    completed_ngc_ids = completed_ids & ngc_ids
    return EditorialAuditReport(
        catalogue_objects=len(catalogue),
        ngc_only_objects=len(ngc_ids),
        baseline_objects=len(baseline_ids),
        completed_objects=len(completed_ids),
        completed_ngc_objects=len(completed_ngc_ids),
        remaining_ngc_objects=len(ngc_ids - completed_ngc_ids),
        accepted_batches=len(accepted_manifests),
        draft_batches=sum(manifest.status == "draft" for manifest in manifests),
        baseline_description_template_families=len(baseline_description_templates),
        baseline_description_template_objects=baseline_description_template_objects,
        baseline_observing_template_families=len(baseline_observing_templates),
        baseline_observing_template_objects=baseline_observing_template_objects,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch",
        type=Path,
        help="also run near-duplicate screening for one batch manifest",
    )
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = audit_catalogue_editorial(batch_path=args.batch)
    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        outcome = "passed" if report.ok else "failed"
        print(
            f"Catalogue editorial audit {outcome}: {report.completed_objects} complete "
            f"objects ({report.baseline_objects} baseline, "
            f"{report.completed_ngc_objects} NGC-only); "
            f"{report.remaining_ngc_objects} NGC-only remaining; "
            f"{report.accepted_batches} accepted batches."
        )
        for warning in report.warnings:
            print(f"WARNING: {warning}")
        for error in report.errors:
            print(f"FAILED: {error}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
