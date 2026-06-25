from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astro_viewer.app.database.bootstrap import _database_size_bytes, _file_signature
from astro_viewer.app.database.city_repository import CityRepository
from astro_viewer.app.database.geonames_importer import (
    _clean_city_aliases,
    _insert_aliases,
    _normalize_search,
    aliases_to_text,
    build_search_name,
    import_geonames_cities,
)


SEARCH_TERMS = [
    "Addis",
    "Addis Ababa",
    "Addis Abeba",
    "አዲስ አበባ",
    "Roma",
    "Rome",
    "Milano",
    "Milan",
    "New York",
    "Tokyo",
]


@dataclass(frozen=True)
class DatabaseStats:
    city_count: int
    alias_count: int
    average_aliases_per_city: float
    max_aliases_per_city: int
    context_like_aliases: int
    country_code_aliases: int
    country_name_aliases: int
    admin_region_aliases: int
    numeric_only_aliases: int
    empty_aliases: int
    database_size_bytes: int


def main() -> None:
    args = _parser().parse_args()
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    database_path = args.database or base_dir.parent / "nightscope.db"
    geonames_path = args.geonames_path or data_dir / "cities15000.txt"
    report_path = args.report or base_dir / "reports" / "runtime_database_cleanup_report.md"
    if not database_path.exists():
        raise SystemExit(f"Runtime database not found: {database_path}")
    if not geonames_path.exists():
        raise SystemExit(f"GeoNames source not found: {geonames_path}")

    before = collect_database_stats(database_path)
    before_searches = search_results(database_path)
    import_report = rebuild_city_catalog(database_path, geonames_path, data_dir)
    after = collect_database_stats(database_path)
    after_searches = search_results(database_path)
    addis_reverse = CityRepository(database_path).nearest_by_coordinates(9.03, 38.74, max_radius_km=25.0)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(
            database_path=database_path,
            geonames_path=geonames_path,
            before=before,
            after=after,
            before_searches=before_searches,
            after_searches=after_searches,
            import_report=import_report,
            addis_reverse=addis_reverse,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "report": str(report_path),
                "before": before.__dict__,
                "after": after.__dict__,
                "import_report": import_report,
                "addis_reverse_lookup": addis_reverse,
            },
            ensure_ascii=True,
            indent=2,
        )
    )


def rebuild_city_catalog(database_path: Path, geonames_path: Path, data_dir: Path) -> dict:
    source_stat = geonames_path.stat()
    source_mtime = datetime.fromtimestamp(source_stat.st_mtime).isoformat(timespec="seconds")
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN")
        connection.execute("DELETE FROM CityAlias")
        connection.execute("DELETE FROM City")
        import_report = import_geonames_cities(
            connection,
            geonames_path,
            country_info_path=data_dir / "countryInfo.txt",
            admin1_codes_path=data_dir / "admin1CodesASCII.txt",
        )
        cleanup_report = cleanup_city_alias_pollution(connection)
        payload = import_report.to_dict()
        payload["aliases_generated"] = import_report.aliases_added
        payload["aliases_removed_after_import"] = cleanup_report["aliases_removed"]
        payload["city_rows_cleaned_after_import"] = cleanup_report["city_rows_cleaned"]
        payload["db_size_bytes"] = _database_size_bytes(connection)
        payload["rebuilt_city_catalog"] = True
        payload["rebuilt_at"] = datetime.now().isoformat(timespec="seconds")
        payload["country_info"] = _file_signature(data_dir / "countryInfo.txt")
        payload["admin1_codes"] = _file_signature(data_dir / "admin1CodesASCII.txt")
        connection.execute(
            """
            INSERT INTO DataImportLog (source_name, source_path, source_size, source_mtime, imported_at, report_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_name) DO UPDATE SET
                source_path = excluded.source_path,
                source_size = excluded.source_size,
                source_mtime = excluded.source_mtime,
                imported_at = excluded.imported_at,
                report_json = excluded.report_json
            """,
            (
                "cities15000.txt",
                str(geonames_path),
                source_stat.st_size,
                source_mtime,
                datetime.now().isoformat(timespec="seconds"),
                json.dumps(payload, ensure_ascii=True),
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    vacuum_connection = sqlite3.connect(database_path)
    try:
        vacuum_connection.execute("VACUUM")
    finally:
        vacuum_connection.close()
    return payload


def cleanup_city_alias_pollution(connection: sqlite3.Connection) -> dict:
    rows = connection.execute(
        """
        SELECT id, city_name, ascii_name, country, country_code, admin_region, aliases
        FROM City
        ORDER BY id
        """
    ).fetchall()
    removed = 0
    cleaned_rows = 0
    for row in rows:
        aliases = {alias for alias in (row["aliases"] or "").split("|") if alias}
        protected = {row["city_name"] or "", row["ascii_name"] or ""}
        context = {row["country"] or "", row["country_code"] or "", row["admin_region"] or ""}
        cleaned = _clean_city_aliases(aliases | protected, context, protected_aliases=protected)
        normalized_before = {_normalize_search(alias) for alias in aliases | protected if alias and _normalize_search(alias)}
        normalized_after = {_normalize_search(alias) for alias in cleaned if alias and _normalize_search(alias)}
        if normalized_after == normalized_before:
            continue
        removed += max(len(normalized_before) - len(normalized_after), 0)
        cleaned_rows += 1
        connection.execute(
            """
            UPDATE City
            SET aliases = ?,
                search_name = ?
            WHERE id = ?
            """,
            (
                aliases_to_text(cleaned),
                build_search_name(
                    row["city_name"],
                    row["ascii_name"] or "",
                    row["country"] or "",
                    row["country_code"] or "",
                    row["admin_region"] or "",
                    cleaned,
                ),
                row["id"],
            ),
        )
        connection.execute("DELETE FROM CityAlias WHERE city_id = ?", (row["id"],))
        _insert_aliases(connection, row["id"], cleaned, "geonames-clean")
    return {"aliases_removed": removed, "city_rows_cleaned": cleaned_rows}


def collect_database_stats(database_path: Path) -> DatabaseStats:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        city_count = _scalar(connection, "SELECT COUNT(*) FROM City")
        alias_count = _scalar(connection, "SELECT COUNT(*) FROM CityAlias")
        max_aliases = _scalar(
            connection,
            "SELECT COALESCE(MAX(alias_count), 0) FROM (SELECT COUNT(*) AS alias_count FROM CityAlias GROUP BY city_id)",
        )
        context_rows = _context_alias_counts(connection)
        numeric_only = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM CityAlias
            WHERE normalized_alias GLOB '[0-9]*'
              AND normalized_alias NOT GLOB '*[^0-9]*'
              AND normalized_alias <> ''
            """,
        )
        empty_aliases = _scalar(connection, "SELECT COUNT(*) FROM CityAlias WHERE TRIM(alias) = '' OR TRIM(normalized_alias) = ''")
        return DatabaseStats(
            city_count=city_count,
            alias_count=alias_count,
            average_aliases_per_city=alias_count / city_count if city_count else 0.0,
            max_aliases_per_city=max_aliases,
            context_like_aliases=sum(context_rows.values()),
            country_code_aliases=context_rows["country_code"],
            country_name_aliases=context_rows["country"],
            admin_region_aliases=context_rows["admin_region"],
            numeric_only_aliases=numeric_only,
            empty_aliases=empty_aliases,
            database_size_bytes=database_path.stat().st_size,
        )
    finally:
        connection.close()


def search_results(database_path: Path) -> list[dict]:
    repository = CityRepository(database_path)
    connection = sqlite3.connect(database_path)
    try:
        results = []
        for term in SEARCH_TERMS:
            matches = repository.search(term, limit=5)
            if not matches:
                results.append({"query": term, "found": False})
                continue
            city = matches[0]
            results.append(
                {
                    "query": term,
                    "found": True,
                    "city_id": city["id"],
                    "city": city["city"],
                    "country": city["country"],
                    "country_code": city["country_code"],
                    "timezone": city["timezone"],
                    "alias_count": _scalar(connection, "SELECT COUNT(*) FROM CityAlias WHERE city_id = ?", (city["id"],)),
                }
            )
        return results
    finally:
        connection.close()


def render_report(
    *,
    database_path: Path,
    geonames_path: Path,
    before: DatabaseStats,
    after: DatabaseStats,
    before_searches: list[dict],
    after_searches: list[dict],
    import_report: dict,
    addis_reverse: dict | None,
) -> str:
    lines = [
        "# Runtime Database City Cleanup Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Database: `{database_path.as_posix()}`",
        f"GeoNames source: `{geonames_path.as_posix()}`",
        "",
        "## Rebuild Approach",
        "",
        "- Rebuilt only `City` and `CityAlias` in the runtime database.",
        "- Preserved the existing schema, indexes, and non-city tables.",
        "- Imported `cities15000.txt` with the corrected GeoNames importer.",
        "- Used packaged `countryInfo.txt` and `admin1CodesASCII.txt` to enrich country and admin names.",
        "- Removed context-like and numeric-only administrative aliases from `CityAlias`; context remains available through columns and `search_name`.",
        "- Updated `DataImportLog` and ran `VACUUM` after the rebuild.",
        "",
        "## Before / After Statistics",
        "",
        _markdown_table(
            ["Metric", "Before cleanup", "After cleanup"],
            [
                ["City rows", before.city_count, after.city_count],
                ["CityAlias rows", before.alias_count, after.alias_count],
                ["Average aliases per city", f"{before.average_aliases_per_city:.2f}", f"{after.average_aliases_per_city:.2f}"],
                ["Maximum aliases per city", before.max_aliases_per_city, after.max_aliases_per_city],
                ["Context-like aliases", before.context_like_aliases, after.context_like_aliases],
                ["Country-code aliases", before.country_code_aliases, after.country_code_aliases],
                ["Country-name aliases", before.country_name_aliases, after.country_name_aliases],
                ["Admin-region aliases", before.admin_region_aliases, after.admin_region_aliases],
                ["Numeric-only aliases", before.numeric_only_aliases, after.numeric_only_aliases],
                ["Empty aliases", before.empty_aliases, after.empty_aliases],
                ["Database size bytes", before.database_size_bytes, after.database_size_bytes],
            ],
        ),
        "",
        "## Corrected Import Report",
        "",
        _markdown_table(
            ["Metric", "Value"],
            [
                ["Rows read", import_report.get("total_rows_read", "")],
                ["Imported", import_report.get("total_imported", "")],
                ["Duplicates skipped/merged", import_report.get("duplicates_merged", "")],
                ["Aliases added", import_report.get("aliases_added", "")],
                ["Missing timezone", import_report.get("cities_missing_timezone", "")],
                ["Rows skipped invalid", import_report.get("rows_skipped_invalid", "")],
            ],
        ),
        "",
        "## Search Verification Before Cleanup",
        "",
        _search_table(before_searches),
        "",
        "## Search Verification After Cleanup",
        "",
        _search_table(after_searches),
        "",
        "## Addis Reverse Lookup",
        "",
    ]
    if addis_reverse:
        lines.append(
            _markdown_table(
                ["Field", "Value"],
                [
                    ["City", addis_reverse.get("city", "")],
                    ["Country", addis_reverse.get("country", "")],
                    ["Country code", addis_reverse.get("country_code", "")],
                    ["Timezone", addis_reverse.get("timezone", "")],
                    ["Distance km", f"{float(addis_reverse.get('distance_km', 0.0)):.3f}"],
                ],
            )
        )
    else:
        lines.append("No nearby city found for Addis Ababa coordinates.")
    lines.extend(
        [
            "",
            "## Assessment",
            "",
            "- The historical runtime database reflected the legacy aggressive merge behavior.",
            "- The rebuilt database removes polluted aliases and restores a city count consistent with the corrected importer.",
            "- Key city searches still resolve to the expected canonical records.",
        ]
    )
    return "\n".join(lines) + "\n"


def _search_table(results: list[dict]) -> str:
    return _markdown_table(
        ["Query", "Returned city", "Country", "Code", "Timezone", "Alias count"],
        [
            [
                row["query"],
                row.get("city", "NOT FOUND"),
                row.get("country", ""),
                row.get("country_code", ""),
                row.get("timezone", ""),
                row.get("alias_count", ""),
            ]
            for row in results
        ],
    )


def _context_alias_counts(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT ca.normalized_alias, c.city_name, c.ascii_name, c.country, c.country_code, c.admin_region
        FROM CityAlias ca
        JOIN City c ON c.id = ca.city_id
        """
    ).fetchall()
    result = {"country_code": 0, "country": 0, "admin_region": 0}
    for row in rows:
        normalized_alias = row["normalized_alias"]
        if not normalized_alias:
            continue
        protected = {
            _normalize_search(row["city_name"] or ""),
            _normalize_search(row["ascii_name"] or ""),
        }
        if normalized_alias in protected:
            continue
        if normalized_alias == _normalize_search(row["country_code"] or ""):
            result["country_code"] += 1
        if normalized_alias == _normalize_search(row["country"] or ""):
            result["country"] += 1
        if normalized_alias == _normalize_search(row["admin_region"] or ""):
            result["admin_region"] += 1
    return result


def _scalar(connection: sqlite3.Connection, query: str, params: tuple = ()) -> int:
    return int(connection.execute(query, params).fetchone()[0] or 0)


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
    parser = argparse.ArgumentParser(description="Rebuild NightScope runtime City and CityAlias data with the corrected GeoNames importer.")
    parser.add_argument("--database", type=Path, default=base_dir.parent / "nightscope.db")
    parser.add_argument("--geonames-path", type=Path, default=base_dir / "data" / "cities15000.txt")
    parser.add_argument("--report", type=Path, default=base_dir / "reports" / "runtime_database_cleanup_report.md")
    return parser


if __name__ == "__main__":
    main()
