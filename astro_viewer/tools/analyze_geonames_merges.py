from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import statistics
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.geonames_importer import (
    GeoNamesCity,
    _clean_city_aliases,
    _distance_km,
    _insert_aliases,
    _is_non_city_row,
    _iter_source_rows,
    _load_admin1_names,
    _load_country_names,
    _normalize_search,
    _optional_int,
    _split_aliases,
    aliases_to_text,
    build_search_name,
)


REASONS = ("alias merge", "same coordinates", "near coordinates", "normalized name match", "other")


@dataclass(frozen=True)
class MergeEvent:
    source_order: int
    source_geonameid: str
    source_name: str
    source_ascii_name: str
    source_latitude: float
    source_longitude: float
    source_population: int | None
    target_id: int
    target_city_name: str
    target_ascii_name: str
    target_latitude: float
    target_longitude: float
    target_population: int | None
    country_code: str
    timezone: str
    distance_km: float
    reason: str
    trigger: str
    shared_aliases: tuple[str, ...]


def main() -> None:
    args = _parser().parse_args()
    base_dir = Path(__file__).resolve().parents[1]
    geonames_path = args.geonames_path or base_dir / "data" / "cities15000.txt"
    report_path = args.report or base_dir / "reports" / "geonames_merge_analysis_report.md"
    if not geonames_path.exists():
        raise SystemExit(f"GeoNames source not found: {geonames_path}")

    legacy_events = reconstruct_merge_events(
        base_dir=base_dir,
        geonames_path=geonames_path,
        include_context_aliases=True,
        proximity_km=args.proximity_km,
    )
    fixed_events = reconstruct_merge_events(
        base_dir=base_dir,
        geonames_path=geonames_path,
        include_context_aliases=False,
        proximity_km=args.proximity_km,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _render_report(legacy_events, fixed_events, geonames_path, args.proximity_km),
        encoding="utf-8",
    )

    print(json.dumps(_summary_payload(legacy_events, fixed_events, report_path), indent=2, ensure_ascii=False))


def reconstruct_merge_events(
    *,
    base_dir: Path,
    geonames_path: Path,
    include_context_aliases: bool,
    proximity_km: float,
) -> list[MergeEvent]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        schema_path = _copy_baseline_city_seed(base_dir, temp_path)
        database_path = temp_path / "nightscope-merge-analysis.db"
        initialize_database(database_path, schema_path)
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        try:
            return _replay_import(
                connection,
                geonames_path,
                include_context_aliases=include_context_aliases,
                proximity_km=proximity_km,
            )
        finally:
            connection.close()


def _copy_baseline_city_seed(base_dir: Path, temp_path: Path) -> Path:
    data_dir = base_dir / "data"
    schema_path = temp_path / "schema.sql"
    shutil.copy2(data_dir / "schema.sql", schema_path)
    shutil.copy2(data_dir / "cities_seed.csv", temp_path / "cities_seed.csv")
    return schema_path


def _replay_import(
    connection: sqlite3.Connection,
    geonames_path: Path,
    *,
    include_context_aliases: bool,
    proximity_km: float,
) -> list[MergeEvent]:
    country_names = _load_country_names(None)
    admin_names = _load_admin1_names(None)
    merge_events: list[MergeEvent] = []
    source_order = 0
    for raw_row in _iter_source_rows(geonames_path):
        source_order += 1
        city = _city_from_row(raw_row, country_names, admin_names, include_context_aliases=include_context_aliases)
        if city is None or not city.timezone:
            continue
        duplicate = _find_duplicate_city_with_reason(
            connection,
            city,
            proximity_km=proximity_km,
            include_context_aliases=include_context_aliases,
        )
        if duplicate is None:
            _insert_city(connection, city)
            continue
        target, distance_km, reason, trigger, shared_aliases = duplicate
        merge_events.append(
            MergeEvent(
                source_order=source_order,
                source_geonameid=city.geonameid,
                source_name=city.city_name,
                source_ascii_name=city.ascii_name,
                source_latitude=city.latitude,
                source_longitude=city.longitude,
                source_population=city.population,
                target_id=int(target["id"]),
                target_city_name=target["city_name"],
                target_ascii_name=target["ascii_name"] or "",
                target_latitude=float(target["latitude"]),
                target_longitude=float(target["longitude"]),
                target_population=target["population"],
                country_code=city.country_code,
                timezone=city.timezone,
                distance_km=distance_km,
                reason=reason,
                trigger=trigger,
                shared_aliases=tuple(sorted(shared_aliases)[:8]),
            )
        )
        _merge_city_aliases(connection, target, city)
    connection.commit()
    return merge_events


def _city_from_row(
    raw_row: dict,
    country_names: dict[str, str],
    admin_names: dict[str, str],
    *,
    include_context_aliases: bool,
) -> GeoNamesCity | None:
    if _is_non_city_row(raw_row):
        return None
    name = (raw_row.get("name") or raw_row.get("city_name") or "").strip()
    ascii_name = (raw_row.get("asciiname") or raw_row.get("ascii_name") or name).strip()
    country_code = (raw_row.get("country_code") or "").strip().upper()
    country = (raw_row.get("country") or country_names.get(country_code) or country_code).strip()
    admin_code = (raw_row.get("admin1_code") or "").strip()
    admin_region = (raw_row.get("admin_region") or admin_names.get(f"{country_code}.{admin_code}") or admin_code).strip()
    timezone = (raw_row.get("timezone") or "").strip()
    try:
        latitude = float(raw_row.get("latitude") or "")
        longitude = float(raw_row.get("longitude") or "")
    except ValueError:
        return None
    if not name or not country_code or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    aliases = _split_aliases(raw_row.get("alternatenames") or raw_row.get("aliases") or "")
    aliases.update({name, ascii_name})
    context_values = {country, country_code, admin_region, admin_code}
    if include_context_aliases:
        aliases.update(context_values)
    else:
        aliases = _clean_city_aliases(aliases, context_values, protected_aliases={name, ascii_name})
    return GeoNamesCity(
        geonameid=str(raw_row.get("geonameid") or ""),
        city_name=name,
        ascii_name=ascii_name,
        country=country,
        country_code=country_code,
        admin_region=admin_region,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        population=_optional_int(raw_row.get("population")),
        aliases=aliases,
    )


def _find_duplicate_city_with_reason(
    connection: sqlite3.Connection,
    city: GeoNamesCity,
    *,
    proximity_km: float,
    include_context_aliases: bool,
) -> tuple[sqlite3.Row, float, str, str, set[str]] | None:
    delta = max(proximity_km / 111.0, 0.01)
    candidates = connection.execute(
        """
        SELECT id, city_name, ascii_name, country, country_code, admin_region,
               latitude, longitude, timezone, population, aliases, search_name
        FROM City
        WHERE country_code = ?
          AND timezone = ?
          AND ABS(latitude - ?) <= ?
          AND ABS(longitude - ?) <= ?
        """,
        (city.country_code, city.timezone, city.latitude, delta, city.longitude, delta),
    ).fetchall()
    city_aliases = {_normalize_search(alias) for alias in city.aliases if _normalize_search(alias)}
    for candidate in candidates:
        distance_km = _distance_km(city.latitude, city.longitude, candidate["latitude"], candidate["longitude"])
        if distance_km > proximity_km:
            continue
        candidate_aliases = _candidate_aliases(connection, candidate, include_context_aliases=include_context_aliases)
        shared_aliases = city_aliases & candidate_aliases
        if shared_aliases:
            return (
                candidate,
                distance_km,
                _classify_reason(city, candidate, distance_km, shared_aliases),
                "alias intersection",
                shared_aliases,
            )
        if _normalize_search(city.ascii_name) == _normalize_search(candidate["ascii_name"] or ""):
            return (candidate, distance_km, "normalized name match", "ascii name equality", set())
    return None


def _classify_reason(city: GeoNamesCity, candidate: sqlite3.Row, distance_km: float, shared_aliases: set[str]) -> str:
    source_names = {_normalize_search(city.city_name), _normalize_search(city.ascii_name)}
    target_names = {_normalize_search(candidate["city_name"] or ""), _normalize_search(candidate["ascii_name"] or "")}
    if source_names & target_names:
        return "normalized name match"
    context_aliases = {
        _normalize_search(city.country),
        _normalize_search(city.country_code),
        _normalize_search(city.admin_region),
        _normalize_search(candidate["country"] or ""),
        _normalize_search(candidate["country_code"] or ""),
        _normalize_search(candidate["admin_region"] or ""),
    }
    meaningful_shared_aliases = {alias for alias in shared_aliases if alias not in context_aliases}
    if meaningful_shared_aliases:
        return "alias merge"
    if distance_km <= 0.05:
        return "same coordinates"
    if distance_km <= 5.0:
        return "near coordinates"
    return "other"


def _candidate_aliases(connection: sqlite3.Connection, candidate: sqlite3.Row, *, include_context_aliases: bool) -> set[str]:
    aliases = {candidate["city_name"] or "", candidate["ascii_name"] or "", *(candidate["aliases"] or "").split("|")}
    if include_context_aliases:
        aliases.update({candidate["country"] or "", candidate["country_code"] or "", candidate["admin_region"] or ""})
    rows = connection.execute(
        "SELECT normalized_alias FROM CityAlias WHERE city_id = ?",
        (candidate["id"],),
    ).fetchall()
    aliases.update(row["normalized_alias"] for row in rows)
    return {_normalize_search(alias) for alias in aliases if alias and _normalize_search(alias)}


def _insert_city(connection: sqlite3.Connection, city: GeoNamesCity) -> int:
    aliases = aliases_to_text(city.aliases)
    cursor = connection.execute(
        """
        INSERT INTO City (
            city_name, ascii_name, country, country_code, admin_region,
            latitude, longitude, timezone, population, aliases, search_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            city.city_name,
            city.ascii_name,
            city.country,
            city.country_code,
            city.admin_region,
            city.latitude,
            city.longitude,
            city.timezone,
            city.population,
            aliases,
            city.search_name,
        ),
    )
    _insert_aliases(connection, int(cursor.lastrowid), city.aliases, "geonames-analysis")
    return int(cursor.lastrowid)


def _merge_city_aliases(connection: sqlite3.Connection, duplicate: sqlite3.Row, city: GeoNamesCity) -> None:
    merged_aliases = {alias for alias in (duplicate["aliases"] or "").split("|") if alias}
    merged_aliases.update(city.aliases)
    population = max(duplicate["population"] or 0, city.population or 0) or None
    search_name = build_search_name(
        duplicate["city_name"],
        duplicate["ascii_name"] or city.ascii_name,
        duplicate["country"] or city.country,
        duplicate["country_code"] or city.country_code,
        duplicate["admin_region"] or city.admin_region,
        merged_aliases,
    )
    connection.execute(
        """
        UPDATE City
        SET aliases = ?,
            search_name = ?,
            population = ?,
            ascii_name = COALESCE(NULLIF(ascii_name, ''), ?),
            admin_region = COALESCE(NULLIF(admin_region, ''), ?)
        WHERE id = ?
        """,
        (
            aliases_to_text(merged_aliases),
            search_name,
            population,
            city.ascii_name,
            city.admin_region,
            duplicate["id"],
        ),
    )
    _insert_aliases(connection, duplicate["id"], merged_aliases, "geonames-analysis")


def _render_report(
    legacy_events: list[MergeEvent],
    fixed_events: list[MergeEvent],
    geonames_path: Path,
    proximity_km: float,
) -> str:
    distances = [event.distance_km for event in legacy_events]
    reason_counts = Counter(event.reason for event in legacy_events)
    fixed_reason_counts = Counter(event.reason for event in fixed_events)
    top_events = sorted(legacy_events, key=lambda event: event.distance_km, reverse=True)[:100]
    lines: list[str] = [
        "# GeoNames Merge Analysis Report",
        "",
        f"Source: `{geonames_path.as_posix()}`",
        f"Deduplication radius: {proximity_km:.1f} km",
        "",
        "This report reconstructs the historical 5,857 merge run using the legacy importer behavior that treated country, country code, and admin region as city aliases. It also computes the merge count with the corrected importer behavior for comparison.",
        "",
        "## Summary",
        "",
        _markdown_table(
            ["Metric", "Legacy run", "Corrected importer replay"],
            [
                ["Merged records", len(legacy_events), len(fixed_events)],
                ["Average distance", _format_km(statistics.fmean(distances) if distances else 0.0), _format_km(statistics.fmean([event.distance_km for event in fixed_events]) if fixed_events else 0.0)],
                ["Max distance", _format_km(max(distances) if distances else 0.0), _format_km(max((event.distance_km for event in fixed_events), default=0.0))],
                ["Suspicious > 1 km", _count_over(legacy_events, 1.0), _count_over(fixed_events, 1.0)],
                ["Suspicious > 5 km", _count_over(legacy_events, 5.0), _count_over(fixed_events, 5.0)],
                ["Suspicious > 10 km", _count_over(legacy_events, 10.0), _count_over(fixed_events, 10.0)],
            ],
        ),
        "",
        "## Count By Merge Reason",
        "",
        _markdown_table(
            ["Reason", "Legacy count", "Corrected importer count"],
            [[reason, reason_counts.get(reason, 0), fixed_reason_counts.get(reason, 0)] for reason in REASONS],
        ),
        "",
        "Reason definitions:",
        "",
        "- `normalized name match`: canonical or ASCII city names match after normalization.",
        "- `alias merge`: source and target share a non-context alternate city name.",
        "- `same coordinates`: merge was effectively driven only by context aliases, but coordinates are within 50 m.",
        "- `near coordinates`: merge was effectively driven only by context aliases, and coordinates are within the dedupe radius but farther than 50 m.",
        "- `other`: merge did not fit the categories above.",
        "",
        "## Top 100 Merge Examples By Distance",
        "",
        _markdown_table(
            [
                "#",
                "Reason",
                "Distance",
                "Country",
                "Timezone",
                "Source GeoNames record",
                "Target City record",
                "Trigger/shared aliases",
            ],
            [
                [
                    index,
                    event.reason,
                    _format_km(event.distance_km),
                    event.country_code,
                    event.timezone,
                    _source_summary(event),
                    _target_summary(event),
                    _trigger_summary(event),
                ]
                for index, event in enumerate(top_events, start=1)
            ],
        ),
        "",
        "## Top Examples Grouped By Reason",
        "",
        *_grouped_example_sections(legacy_events),
        "## Suspicious Merge Buckets",
        "",
    ]
    for threshold in (1.0, 5.0, 10.0):
        suspicious = [event for event in legacy_events if event.distance_km > threshold]
        by_reason = Counter(event.reason for event in suspicious)
        lines.extend(
            [
                f"### Distance > {threshold:g} km",
                "",
                _markdown_table(
                    ["Reason", "Count"],
                    [[reason, by_reason.get(reason, 0)] for reason in REASONS],
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## Assessment",
            "",
            _assessment(legacy_events, fixed_events),
        ]
    )
    return "\n".join(lines) + "\n"


def _grouped_example_sections(events: list[MergeEvent]) -> list[str]:
    lines: list[str] = []
    for reason in REASONS:
        reason_events = sorted(
            (event for event in events if event.reason == reason),
            key=lambda event: event.distance_km,
            reverse=True,
        )[:10]
        lines.extend([f"### {reason}", ""])
        if not reason_events:
            lines.extend(["No merge examples for this reason.", ""])
            continue
        lines.extend(
            [
                _markdown_table(
                    [
                        "#",
                        "Distance",
                        "Country",
                        "Timezone",
                        "Source GeoNames record",
                        "Target City record",
                        "Trigger/shared aliases",
                    ],
                    [
                        [
                            index,
                            _format_km(event.distance_km),
                            event.country_code,
                            event.timezone,
                            _source_summary(event),
                            _target_summary(event),
                            _trigger_summary(event),
                        ]
                        for index, event in enumerate(reason_events, start=1)
                    ],
                ),
                "",
            ]
        )
    return lines


def _assessment(legacy_events: list[MergeEvent], fixed_events: list[MergeEvent]) -> str:
    legacy_near = sum(1 for event in legacy_events if event.reason == "near coordinates")
    legacy_strong = sum(1 for event in legacy_events if event.reason in {"normalized name match", "alias merge", "same coordinates"})
    removed_by_fix = len(legacy_events) - len(fixed_events)
    return "\n".join(
        [
            f"- The legacy run produced {len(legacy_events)} merges. Of these, {legacy_strong} have a strong name/alias or same-coordinate signal, while {legacy_near} are near-coordinate context-only merges.",
            f"- Replaying with the corrected importer produces {len(fixed_events)} merges, reducing the merge count by {removed_by_fix}.",
            "- A high count of `near coordinates` merges is evidence that the old deduplication was too aggressive because country/admin aliases made unrelated nearby settlements look related.",
            "- Legitimate translated-name merges, including cases like Addis Ababa/Addis Abeba, should remain in the corrected replay because they share real city aliases.",
        ]
    )


def _summary_payload(legacy_events: list[MergeEvent], fixed_events: list[MergeEvent], report_path: Path) -> dict:
    distances = [event.distance_km for event in legacy_events]
    return {
        "report": str(report_path),
        "legacy_merges": len(legacy_events),
        "corrected_importer_merges": len(fixed_events),
        "count_by_reason": dict(Counter(event.reason for event in legacy_events)),
        "average_distance_km": round(statistics.fmean(distances), 3) if distances else 0.0,
        "max_distance_km": round(max(distances), 3) if distances else 0.0,
        "suspicious_gt_1km": _count_over(legacy_events, 1.0),
        "suspicious_gt_5km": _count_over(legacy_events, 5.0),
        "suspicious_gt_10km": _count_over(legacy_events, 10.0),
    }


def _count_over(events: list[MergeEvent], threshold_km: float) -> int:
    return sum(1 for event in events if event.distance_km > threshold_km)


def _format_km(value: float) -> str:
    return f"{value:.3f} km"


def _source_summary(event: MergeEvent) -> str:
    return (
        f"{event.source_geonameid}: {event.source_name} / {event.source_ascii_name} "
        f"pop={event.source_population or 0} @ {event.source_latitude:.5f},{event.source_longitude:.5f}"
    )


def _target_summary(event: MergeEvent) -> str:
    return (
        f"{event.target_id}: {event.target_city_name} / {event.target_ascii_name} "
        f"pop={event.target_population or 0} @ {event.target_latitude:.5f},{event.target_longitude:.5f}"
    )


def _trigger_summary(event: MergeEvent) -> str:
    aliases = ", ".join(event.shared_aliases)
    return f"{event.trigger}: {aliases}" if aliases else event.trigger


def _markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        cells = []
        for value in row:
            text = "" if value is None else str(value)
            cells.append(text.replace("|", "\\|").replace("\n", " "))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    base_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Reconstruct and report GeoNames city merge decisions.")
    parser.add_argument("--geonames-path", type=Path, default=base_dir / "data" / "cities15000.txt")
    parser.add_argument("--report", type=Path, default=base_dir / "reports" / "geonames_merge_analysis_report.md")
    parser.add_argument("--proximity-km", type=float, default=5.0)
    return parser


if __name__ == "__main__":
    main()
